import json
from hashlib import sha256
from math import asin, cos, isfinite, radians, sin, sqrt
from urllib.parse import urlencode, urlparse

import requests
from django.core.cache import cache
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from core.models import ObjectType
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from dcim.api.views import DeviceViewSet
from dcim.models import Device
from extras.models import SavedFilter
from rest_framework.exceptions import ValidationError as APIValidationError

from .forms import (
    GeoViewFilterForm,
    GeoViewSavedFilterForm,
    get_saved_filter_models,
    get_usable_saved_filters,
)
from .permissions import GeoViewPermissionRequiredMixin, can_view_geoview
from .polyline import decode_polyline
from .version import __version__
from .filters import (
    DEVICE_FILTER_FIELDS,
    SITE_FILTER_FIELDS,
    as_querydict,
    filter_operators,
    normalize_parameters,
    resolve_filter_parameters,
    serialize_parameters,
)
from .services.maps import GeoViewMapService

# Backwards-compatible helper import for existing integrations.
apply_saved_filter_parameters = resolve_filter_parameters


class GeoViewConfigMixin(GeoViewPermissionRequiredMixin, GeoViewMapService):
    pass


class GeoViewDeviceChoicesView(GeoViewConfigMixin, DeviceViewSet):
    """Keep NetBox's device selector aligned with GeoView role operators."""

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        try:
            parameters = normalize_parameters(
                {
                    "role": self.request.query_params.getlist("geoview_role"),
                    "role_op": self.request.query_params.get("geoview_role_op", "exact"),
                },
                strict=True,
            )
        except ValidationError as exc:
            raise APIValidationError(exc.messages) from exc
        form = GeoViewFilterForm(data=parameters, user=self.request.user)
        if not form.is_valid():
            raise APIValidationError(form.errors)
        return self.apply_role_filter(
            queryset, form.cleaned_data["role"], parameters["role_op"]
        )


class GeoViewBaseView(GeoViewConfigMixin, TemplateView):
    active_tab = "map"

    def get_initial_values(self):
        min_zoom, _ = self.get_zoom_bounds()
        return {
            "lat": self.get_setting("start_latitude", "map_center_lat"),
            "lon": self.get_setting("start_longitude", "map_center_lon"),
            "zoom": self.clamp_zoom(
                self.get_setting("start_zoom", "map_zoom") or min_zoom
            ),
        }

    def get_form(self):
        try:
            data = resolve_filter_parameters(self.request.GET, self.request.user)
            error = None
        except ValidationError as exc:
            data, error = self.request.GET.copy(), exc
        form = GeoViewFilterForm(data=data, user=self.request.user)
        form.is_valid()
        if error:
            form.add_error(None, error)
        return form

    def get_cleaned_data(self, form):
        if form.is_valid():
            return form.cleaned_data
        return {}

    def get_map_state(self):
        return self.get_initial_values()

    def get_filter_operators(self):
        return filter_operators(self.get_form().data)

    def build_tab_url(self, view_name):
        base_url = reverse(view_name)
        query_string = self.request.GET.urlencode()
        if query_string:
            return f"{base_url}?{query_string}"
        return base_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_form()
        cleaned_data = self.get_cleaned_data(form)
        operators = filter_operators(form.data)
        map_state = self.get_map_state()
        filtered_sites = self.get_filtered_sites(cleaned_data, operators)
        filtered_devices = self.get_filtered_devices(cleaned_data, operators)
        has_active_filters = self.get_active_filter_count(cleaned_data) > 0
        routing_config = self.get_routing_config()
        active_filter_badges = []
        for group in self.build_selection_groups(cleaned_data, operators):
            entries = ", ".join(group["entries"])
            if entries:
                operator = group.get("operator", "exact")
                if group["label"] == _("Tags"):
                    relation = (
                        _("does not have these tags")
                        if operator == "n"
                        else _("has these tags")
                    )
                else:
                    relation = _("is not") if operator == "n" else _("is")
                active_filter_badges.append(f"{group['label']} {relation}: {entries}")

        save_filter_url = None
        if (
            has_active_filters
            and self.request.user.has_perm("extras.add_savedfilter")
            and not form.errors
        ):
            save_filter_url = (
                reverse("plugins:netbox_geoview:savedfilter_add")
                + "?"
                + as_querydict(serialize_parameters(form.data)).urlencode()
            )
        references = self.request.GET.getlist("filter_id") + self.request.GET.getlist(
            "filter"
        )
        source_filter_id = self.request.GET.get("source_filter_id")
        if len(references) == 1:
            source_filter_id = self.request.GET.get("filter_id")
        if (
            len(references) == 1
            and not source_filter_id
            and self.request.GET.get("filter")
        ):
            saved = (
                get_usable_saved_filters(self.request.user)
                .filter(slug=self.request.GET["filter"])
                .first()
            )
            source_filter_id = saved.pk if saved else None
        source_filter = (
            get_usable_saved_filters(self.request.user)
            .filter(pk=source_filter_id)
            .first()
            if str(source_filter_id).isdigit()
            else None
        )
        update_filter_url = None
        if (
            source_filter
            and not form.errors
            and self.request.user.has_perm("extras.change_savedfilter")
        ):
            editable = SavedFilter.objects.restrict(self.request.user, "change").filter(
                pk=source_filter.pk
            )
            if editable.exists() and (
                source_filter.user_id == self.request.user.pk
                or self.request.user.is_superuser
            ):
                update_filter_url = (
                    reverse(
                        "plugins:netbox_geoview:savedfilter_edit",
                        args=[source_filter.pk],
                    )
                    + "?"
                    + as_querydict(serialize_parameters(form.data)).urlencode()
                )
        context.update(
            {
                "model": Device,
                "active_tab": self.active_tab,
                "filter_form": form,
                "map_state": map_state,
                "map_config": self.get_map_config(
                    map_state, filtered_sites, filtered_devices, has_active_filters
                ),
                "map_url": self.build_tab_url("plugins:netbox_geoview:map"),
                "filter_url": self.build_tab_url("plugins:netbox_geoview:filter"),
                "apply_url": reverse("plugins:netbox_geoview:apply"),
                "map_base_url": reverse("plugins:netbox_geoview:map"),
                "filter_base_url": reverse("plugins:netbox_geoview:filter"),
                "selection_groups": self.build_selection_groups(
                    cleaned_data, operators
                ),
                "selection_counts": {
                    "sites": filtered_sites.count(),
                    "devices": filtered_devices.count(),
                },
                "active_filter_count": self.get_active_filter_count(cleaned_data),
                "active_filter_badges": active_filter_badges,
                "save_filter_url": save_filter_url,
                "update_filter_url": update_filter_url,
                "source_filter_id": source_filter.pk if source_filter else "",
                "filter_ops": operators,
                "asset_version": f"{__version__}-role-markers-2",
                "routing_profiles": [
                    {
                        "value": option,
                        "label": routing_config["costing_labels"].get(
                            option, option.title()
                        ),
                    }
                    for option in routing_config["costing_options"]
                ],
                "routing_default_profile": routing_config["default_costing"],
            }
        )
        return context


class GeoViewMapView(GeoViewBaseView):
    template_name = "netbox_geoview/map.html"
    active_tab = "map"


class GeoViewFilterView(GeoViewBaseView):
    template_name = "netbox_geoview/map.html"
    active_tab = "filter"


class GeoViewSaveFilterView(GeoViewConfigMixin, View):
    """Edit NetBox SavedFilter objects using GeoView's validated conditions."""

    template_name = "netbox_geoview/savedfilter_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_view_geoview(request.user):
            return self.handle_no_permission()
        self.instance = None
        pk = kwargs.get("pk")
        action = "change" if pk else "add"
        if not request.user.has_perm(f"extras.{action}_savedfilter"):
            raise PermissionDenied
        if pk:
            self.instance = get_object_or_404(
                SavedFilter.objects.restrict(request.user, "change"), pk=pk
            )
            if (
                self.instance.user_id != request.user.pk
                and not request.user.is_superuser
            ):
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, **kwargs):
        try:
            source = (
                self.instance.parameters
                if self.instance and not request.GET
                else request.GET
            )
            parameters = resolve_filter_parameters(
                normalize_parameters(source, strict=True), request.user
            )
            error = None
        except ValidationError as exc:
            parameters, error = as_querydict({}), exc
        form = GeoViewSavedFilterForm(
            instance=self.instance,
            initial={
                "parameters": json.dumps(serialize_parameters(parameters)),
                "shared": self.instance.shared if self.instance else False,
            },
        )
        return render(
            request,
            self.template_name,
            {"form": form, "filter_error": error, "editing": bool(self.instance)},
        )

    def post(self, request, **kwargs):
        form = GeoViewSavedFilterForm(request.POST, instance=self.instance)
        if form.is_valid():
            try:
                parameters = resolve_filter_parameters(
                    form.cleaned_data["parameters"], request.user
                )
                selection = GeoViewFilterForm(data=parameters, user=request.user)
                if not selection.is_valid():
                    raise ValidationError(
                        _("Some filter selections are invalid or no longer accessible.")
                    )
                if not any(
                    selection.cleaned_data.get(field)
                    for field in SITE_FILTER_FIELDS + DEVICE_FILTER_FIELDS
                ):
                    raise ValidationError(
                        _("Select at least one filter condition before saving.")
                    )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                with transaction.atomic():
                    saved = form.save(commit=False)
                    saved.parameters = serialize_parameters(parameters)
                    if not saved.pk:
                        saved.user = request.user
                        saved.enabled = True
                    saved.save()
                    saved.object_types.set(
                        ObjectType.objects.get_for_model(model)
                        for model in get_saved_filter_models(selection.cleaned_data)
                    )
                messages.success(request, _("GeoView filter saved."))
                return redirect(
                    reverse("plugins:netbox_geoview:map")
                    + "?"
                    + urlencode({"filter_id": saved.pk})
                )
        return render(
            request, self.template_name, {"form": form, "editing": bool(self.instance)}
        )


class GeoViewMapDataView(GeoViewBaseView):
    """Read-only widget data; never cache marker payloads across users."""

    def get(self, request, *args, **kwargs):
        if len(request.GET.getlist("filter_id")) != 1 or not request.GET.get(
            "filter_id"
        ):
            return JsonResponse(
                {"error": str(_("Select a saved filter for this widget."))}, status=400
            )
        form = self.get_form()
        if not form.is_valid():
            return JsonResponse(
                {
                    "error": str(
                        _(
                            "The filter is unavailable, incompatible, or contains inaccessible selections."
                        )
                    )
                },
                status=400,
            )
        cleaned = form.cleaned_data
        if not self.get_active_filter_count(cleaned):
            return JsonResponse(
                {"error": str(_("The saved filter has no supported conditions."))},
                status=400,
            )
        operators = filter_operators(form.data)
        sites = self.get_filtered_sites(cleaned, operators)
        devices = self.get_filtered_devices(cleaned, operators)
        config = self.get_map_config(self.get_initial_values(), sites, devices, True)
        config["scroll_wheel_zoom"] = False
        config["fit_bounds"] = request.GET.get("fit_bounds", "1") != "0"
        config["routing"] = {"enabled": False}
        config["ui"]["show_route_actions"] = False
        response = JsonResponse(
            {
                "config": config,
                "map_url": reverse("plugins:netbox_geoview:map")
                + "?"
                + urlencode({"filter_id": request.GET["filter_id"]}),
            }
        )
        response["Cache-Control"] = "private, no-store"
        return response


class GeoViewApplyFiltersView(GeoViewConfigMixin, View):
    http_method_names = ["get"]

    def get(self, request):
        try:
            parameters = resolve_filter_parameters(request.GET, request.user)
        except ValidationError:
            return redirect(
                reverse("plugins:netbox_geoview:map") + "?" + request.GET.urlencode()
            )
        form = GeoViewFilterForm(
            data=parameters,
            user=request.user,
        )
        form.is_valid()
        cleaned_data = form.cleaned_data if form.is_valid() else {}
        selected_devices = cleaned_data.get("device")
        if selected_devices:
            has_unmappable_device = any(
                (device.latitude is None or device.longitude is None)
                and (
                    device.site is None
                    or device.site.latitude is None
                    or device.site.longitude is None
                )
                for device in selected_devices.select_related("site")
            )
        else:
            has_unmappable_device = False
        if has_unmappable_device:
            messages.warning(
                request,
                _(
                    "The selected site does not have coordinates and cannot be shown on the map."
                ),
            )
        query_string = request.GET.urlencode()
        target_url = reverse("plugins:netbox_geoview:map")
        if query_string:
            target_url = f"{target_url}?{query_string}"
        return redirect(target_url)


class GeoViewTileView(GeoViewConfigMixin, View):
    http_method_names = ["get"]

    def get_upstream_url(self, layer_id, z, x, y):
        for layer in self.get_tile_layer_configs():
            if layer["id"] != layer_id:
                continue
            upstream_url = (
                layer["url"]
                .replace("{z}", str(z))
                .replace("{x}", str(x))
                .replace("{y}", str(y))
            )
            if layer["query"]:
                separator = "&" if "?" in upstream_url else "?"
                upstream_url = f"{upstream_url}{separator}{urlencode(layer['query'])}"
            parsed = urlparse(upstream_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise Http404
            return upstream_url, layer["headers"]
        raise Http404

    def get_cache_key(self, upstream_url):
        return f"netbox_geoview.tile.{sha256(upstream_url.encode('utf-8')).hexdigest()}"

    def get(self, request, layer_id, z, x, y):
        min_zoom, max_zoom = self.get_zoom_bounds()
        if z < min_zoom or z > max_zoom:
            raise Http404
        scale = 2**z
        if x < 0 or y < 0 or x >= scale or y >= scale:
            raise Http404

        upstream_url, layer_headers = self.get_upstream_url(layer_id, z, x, y)
        cache_key = self.get_cache_key(upstream_url)
        cached_tile = cache.get(cache_key)
        if cached_tile is not None:
            response = HttpResponse(
                cached_tile["content"], content_type=cached_tile["content_type"]
            )
            response["Cache-Control"] = "private, no-cache"
            return response

        request_headers = {
            "User-Agent": f"netbox-geoview/{__version__}",
            "Referer": request.build_absolute_uri(
                reverse("plugins:netbox_geoview:map")
            ),
        }
        request_headers.update(layer_headers)

        try:
            upstream_response = requests.get(
                upstream_url, headers=request_headers, timeout=10
            )
            if upstream_response.status_code == 404:
                raise Http404
            upstream_response.raise_for_status()
            content = upstream_response.content
            content_type = (upstream_response.headers.get("Content-Type") or "").split(
                ";", 1
            )[0]
        except requests.exceptions.RequestException:
            return HttpResponse(status=502)

        if not content_type.startswith("image/"):
            return HttpResponse(status=502)

        cache.set(
            cache_key,
            {"content": content, "content_type": content_type},
            timeout=86400,
        )
        response = HttpResponse(content, content_type=content_type)
        response["Cache-Control"] = "private, no-cache"
        return response


class GeoViewRouteView(GeoViewConfigMixin, View):
    http_method_names = ["get"]
    LONG_DISTANCE_PROFILES = {"bicycle", "pedestrian"}
    LONG_DISTANCE_LIMIT_METERS = 200000.0

    def get_float_query_param(self, request, key, min_value, max_value):
        raw_value = request.GET.get(key)
        if raw_value is None:
            raise ValueError
        value = float(raw_value)
        if not isfinite(value) or value < min_value or value > max_value:
            raise ValueError
        return value

    def parse_valhalla_error(self, response_data, costing=None):
        if isinstance(response_data, dict):
            long_distance_message = (
                response_data.get("error") or response_data.get("message") or ""
            )
            if (
                costing in self.LONG_DISTANCE_PROFILES
                and isinstance(long_distance_message, str)
                and "Path distance exceeds the max distance limit"
                in long_distance_message
            ):
                return _(
                    "The selected route is too long for the chosen mode. Bicycle and walking routes are limited to about 200 km. Please choose car mode or select points that are closer together."
                )
            for key in ("error", "message"):
                value = response_data.get(key)
                if value:
                    return str(value)
            error_code = response_data.get("error_code")
            error_text = response_data.get("error")
            if error_code and error_text:
                return f"{error_code}: {error_text}"
        return _("Routing service returned an error.")

    def get_distance_unit(self, payload):
        directions_options = payload.get("directions_options", {})
        if not isinstance(directions_options, dict):
            return "km"
        units = str(directions_options.get("units") or "").strip().lower()
        if units == "miles":
            return "mi"
        return "km"

    def calculate_direct_distance_meters(self, start_lat, start_lon, end_lat, end_lon):
        earth_radius_m = 6371000.0
        lat1 = radians(start_lat)
        lon1 = radians(start_lon)
        lat2 = radians(end_lat)
        lon2 = radians(end_lon)
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        haversine = (
            sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        )
        arc = 2 * asin(min(1.0, sqrt(max(0.0, haversine))))
        return earth_radius_m * arc

    def build_route_geometry(self, trip):
        if not isinstance(trip, dict):
            return []
        legs = trip.get("legs")
        if not isinstance(legs, list):
            shape = trip.get("shape")
            if shape:
                return decode_polyline(str(shape), precision=6)
            return []
        geometry = []
        for leg in legs:
            if not isinstance(leg, dict):
                continue
            shape = leg.get("shape")
            if not shape:
                continue
            decoded = decode_polyline(str(shape), precision=6)
            if not decoded:
                continue
            if geometry and geometry[-1] == decoded[0]:
                geometry.extend(decoded[1:])
            else:
                geometry.extend(decoded)
        return geometry

    def normalize_route(self, trip, distance_unit):
        if not isinstance(trip, dict):
            return None
        summary = trip.get("summary", {})
        if not isinstance(summary, dict):
            summary = {}
        try:
            distance = float(summary.get("length", 0))
        except (TypeError, ValueError):
            distance = 0.0
        try:
            duration_seconds = float(summary.get("time", 0))
        except (TypeError, ValueError):
            duration_seconds = 0.0
        geometry = self.build_route_geometry(trip)
        return {
            "distance": round(distance, 3),
            "distance_unit": distance_unit,
            "duration_seconds": round(duration_seconds, 1),
            "duration_minutes": round(duration_seconds / 60, 1),
            "geometry": geometry,
        }

    def build_upstream_url(self):
        base_url = self.get_valhalla_url()
        if not base_url:
            return ""
        query = self.get_valhalla_query()
        if query:
            separator = "&" if "?" in base_url else "?"
            return f"{base_url}{separator}{urlencode(query)}"
        return base_url

    def get(self, request):
        valhalla_url = self.build_upstream_url()
        if not valhalla_url:
            return JsonResponse(
                {
                    "success": False,
                    "error": _("Routing is not configured."),
                },
                status=503,
            )
        try:
            start_lat = self.get_float_query_param(request, "start_lat", -90, 90)
            start_lon = self.get_float_query_param(request, "start_lon", -180, 180)
            end_lat = self.get_float_query_param(request, "end_lat", -90, 90)
            end_lon = self.get_float_query_param(request, "end_lon", -180, 180)
        except (TypeError, ValueError):
            return JsonResponse(
                {
                    "success": False,
                    "error": _("Invalid coordinates."),
                },
                status=400,
            )

        costing_options = self.get_valhalla_costing_options()
        costing = str(
            request.GET.get("costing") or self.get_valhalla_default_costing()
        ).lower()
        if costing not in costing_options:
            costing = self.get_valhalla_default_costing()
        if costing in self.LONG_DISTANCE_PROFILES:
            direct_distance_m = self.calculate_direct_distance_meters(
                start_lat,
                start_lon,
                end_lat,
                end_lon,
            )
            if direct_distance_m > self.LONG_DISTANCE_LIMIT_METERS:
                return JsonResponse(
                    {
                        "success": False,
                        "error": _(
                            "The selected route is too long for the chosen mode. Bicycle and walking routes are limited to about 200 km. Please choose car mode or select points that are closer together."
                        ),
                    },
                    status=400,
                )

        payload = self.get_valhalla_request_defaults()
        payload["locations"] = [
            {"lat": start_lat, "lon": start_lon},
            {"lat": end_lat, "lon": end_lon},
        ]
        payload["costing"] = costing
        distance_unit = self.get_distance_unit(payload)

        request_headers = {
            "User-Agent": f"netbox-geoview/{__version__}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        request_headers.update(self.get_valhalla_headers())

        try:
            upstream_response = requests.post(
                valhalla_url,
                json=payload,
                headers=request_headers,
                timeout=self.get_valhalla_timeout(),
            )
            try:
                response_data = upstream_response.json()
            except ValueError:
                return JsonResponse(
                    {
                        "success": False,
                        "error": _("Routing service returned an invalid response."),
                    },
                    status=502,
                )
            if upstream_response.status_code >= 400:
                return JsonResponse(
                    {
                        "success": False,
                        "error": self.parse_valhalla_error(
                            response_data, costing=costing
                        ),
                    },
                    status=400 if upstream_response.status_code < 500 else 502,
                )
        except requests.exceptions.Timeout:
            return JsonResponse(
                {
                    "success": False,
                    "error": _("Routing service is unavailable."),
                },
                status=502,
            )
        except requests.exceptions.RequestException:
            return JsonResponse(
                {
                    "success": False,
                    "error": _("Routing service is unavailable."),
                },
                status=502,
            )

        trip = response_data.get("trip") if isinstance(response_data, dict) else None
        route = self.normalize_route(trip, distance_unit)
        if not route or not route["geometry"]:
            return JsonResponse(
                {
                    "success": False,
                    "error": _("No route found."),
                },
                status=404,
            )

        alternatives = []
        alternates_raw = (
            response_data.get("alternates", [])
            if isinstance(response_data, dict)
            else []
        )
        if isinstance(alternates_raw, list):
            for alternate in alternates_raw:
                alt_trip = (
                    alternate.get("trip") if isinstance(alternate, dict) else alternate
                )
                normalized = self.normalize_route(alt_trip, distance_unit)
                if normalized and normalized["geometry"]:
                    alternatives.append(normalized)

        return JsonResponse(
            {
                "success": True,
                "route": route,
                "alternatives": alternatives,
                "costing": costing,
            }
        )
