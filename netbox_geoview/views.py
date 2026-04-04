from django.conf import settings
from hashlib import sha256
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from dcim.models import Device
from netbox.plugins import get_plugin_config

from .forms import GeoViewFilterForm
from .version import __version__


class GeoViewBaseView(TemplateView):
    active_tab = "map"

    def get_plugin_settings(self):
        return getattr(settings, "PLUGINS_CONFIG", {}).get("netbox_geoview", {})

    def get_setting(self, *keys):
        plugin_settings = self.get_plugin_settings()
        for key in keys:
            if key in plugin_settings:
                return plugin_settings[key]
        for key in keys:
            value = get_plugin_config("netbox_geoview", key)
            if value is not None:
                return value
        return None

    def get_zoom_bounds(self):
        min_zoom = int(self.get_setting("min_zoom") or 2)
        max_zoom = int(self.get_setting("max_zoom") or 19)
        min_zoom = max(0, min(min_zoom, 22))
        max_zoom = max(0, min(max_zoom, 22))
        if min_zoom > max_zoom:
            min_zoom, max_zoom = max_zoom, min_zoom
        return min_zoom, max_zoom

    def clamp_zoom(self, value):
        min_zoom, max_zoom = self.get_zoom_bounds()
        return max(min_zoom, min(max_zoom, int(value)))

    def get_initial_values(self):
        min_zoom, _ = self.get_zoom_bounds()
        return {
            "lat": self.get_setting("start_latitude", "map_center_lat"),
            "lon": self.get_setting("start_longitude", "map_center_lon"),
            "zoom": self.clamp_zoom(self.get_setting("start_zoom", "map_zoom") or min_zoom),
            "limit": 250,
        }

    def get_form(self):
        data = self.request.GET or None
        min_zoom, max_zoom = self.get_zoom_bounds()
        form = GeoViewFilterForm(
            data=data,
            initial=self.get_initial_values(),
            min_zoom=min_zoom,
            max_zoom=max_zoom,
        )
        if form.is_bound:
            form.is_valid()
        else:
            form.cleaned_data = {}
        return form

    def get_cleaned_data(self, form):
        if form.is_valid():
            return form.cleaned_data
        return {}

    def get_map_state(self, cleaned_data):
        initial = self.get_initial_values()
        return {
            "lat": cleaned_data.get("lat")
            if cleaned_data.get("lat") is not None
            else initial["lat"],
            "lon": cleaned_data.get("lon")
            if cleaned_data.get("lon") is not None
            else initial["lon"],
            "zoom": self.clamp_zoom(
                cleaned_data.get("zoom")
                if cleaned_data.get("zoom") is not None
                else initial["zoom"]
            ),
        }

    def get_preview_limit(self, cleaned_data):
        initial = self.get_initial_values()
        return cleaned_data.get("limit") or initial["limit"]

    def get_filtered_devices(self, cleaned_data):
        queryset = Device.objects.select_related("site", "location", "role").order_by(
            "name"
        )
        query = cleaned_data.get("q")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(serial__icontains=query)
                | Q(asset_tag__icontains=query)
            )
        sites = cleaned_data.get("sites")
        if sites:
            queryset = queryset.filter(site__in=sites)
        locations = cleaned_data.get("locations")
        if locations:
            queryset = queryset.filter(location__in=locations)
        device_roles = cleaned_data.get("device_roles")
        if device_roles:
            queryset = queryset.filter(role__in=device_roles)
        devices = cleaned_data.get("devices")
        if devices:
            queryset = queryset.filter(pk__in=devices.values_list("pk", flat=True))
        return queryset.distinct()

    def build_selection_groups(self, cleaned_data):
        groups = []
        if cleaned_data.get("sites"):
            groups.append(
                {
                    "label": _("Sites"),
                    "entries": [site.name for site in cleaned_data["sites"]],
                }
            )
        if cleaned_data.get("locations"):
            groups.append(
                {
                    "label": _("Locations"),
                    "entries": [
                        location.name for location in cleaned_data["locations"]
                    ],
                }
            )
        if cleaned_data.get("device_roles"):
            groups.append(
                {
                    "label": _("Roles"),
                    "entries": [role.name for role in cleaned_data["device_roles"]],
                }
            )
        if cleaned_data.get("devices"):
            groups.append(
                {
                    "label": _("Devices"),
                    "entries": [
                        device.name or str(device) for device in cleaned_data["devices"]
                    ],
                }
            )
        return groups

    def get_active_filter_count(self, cleaned_data):
        count = 0
        if cleaned_data.get("q"):
            count += 1
        for key in ("sites", "locations", "device_roles", "devices"):
            values = cleaned_data.get(key)
            if values:
                count += 1
        return count

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
        map_state = self.get_map_state(cleaned_data)
        filtered_devices = self.get_filtered_devices(cleaned_data)
        preview_limit = self.get_preview_limit(cleaned_data)
        context.update(
            {
                "model": Device,
                "active_tab": self.active_tab,
                "filter_form": form,
                "map_state": map_state,
                "tile_url": (
                    f"{reverse('plugins:netbox_geoview:map')}"
                    "tiles/{z}/{x}/{y}.png"
                ),
                "map_url": self.build_tab_url("plugins:netbox_geoview:map"),
                "filter_url": self.build_tab_url("plugins:netbox_geoview:filter"),
                "map_base_url": reverse("plugins:netbox_geoview:map"),
                "filter_base_url": reverse("plugins:netbox_geoview:filter"),
                "selection_groups": self.build_selection_groups(cleaned_data),
                "selection_counts": {
                    "sites": len(cleaned_data.get("sites") or []),
                    "locations": len(cleaned_data.get("locations") or []),
                    "roles": len(cleaned_data.get("device_roles") or []),
                    "devices": len(cleaned_data.get("devices") or []),
                },
                "active_filter_count": self.get_active_filter_count(cleaned_data),
                "result_counts": {
                    "devices": filtered_devices.count(),
                    "sites": filtered_devices.exclude(site__isnull=True)
                    .values("site_id")
                    .distinct()
                    .count(),
                    "locations": filtered_devices.exclude(location__isnull=True)
                    .values("location_id")
                    .distinct()
                    .count(),
                },
                "preview_devices": filtered_devices[:preview_limit],
                "preview_limit": preview_limit,
                "map_overlay": {
                    "attribution": "© OpenStreetMap contributors",
                },
            }
        )
        return context


class GeoViewMapView(GeoViewBaseView):
    template_name = "netbox_geoview/map.html"
    active_tab = "map"


class GeoViewFilterView(GeoViewBaseView):
    template_name = "netbox_geoview/map.html"
    active_tab = "filter"


class GeoViewTileView(View):
    http_method_names = ["get"]

    def get_plugin_settings(self):
        return getattr(settings, "PLUGINS_CONFIG", {}).get("netbox_geoview", {})

    def get_setting(self, *keys):
        plugin_settings = self.get_plugin_settings()
        for key in keys:
            if key in plugin_settings:
                return plugin_settings[key]
        for key in keys:
            value = get_plugin_config("netbox_geoview", key)
            if value is not None:
                return value
        return None

    def get_zoom_bounds(self):
        min_zoom = int(self.get_setting("min_zoom") or 2)
        max_zoom = int(self.get_setting("max_zoom") or 19)
        min_zoom = max(0, min(min_zoom, 22))
        max_zoom = max(0, min(max_zoom, 22))
        if min_zoom > max_zoom:
            min_zoom, max_zoom = max_zoom, min_zoom
        return min_zoom, max_zoom

    def get_upstream_url(self, z, x, y):
        template = self.get_setting("tile_provider_url", "tile_url")
        upstream_url = (
            template.replace("{z}", str(z))
            .replace("{x}", str(x))
            .replace("{y}", str(y))
        )
        parsed = urlparse(upstream_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise Http404
        return upstream_url

    def get_cache_key(self, upstream_url):
        return f"netbox_geoview.tile.{sha256(upstream_url.encode('utf-8')).hexdigest()}"

    def get(self, request, z, x, y):
        min_zoom, max_zoom = self.get_zoom_bounds()
        if z < min_zoom or z > max_zoom:
            raise Http404
        scale = 2**z
        if x < 0 or y < 0 or x >= scale or y >= scale:
            raise Http404

        upstream_url = self.get_upstream_url(z, x, y)
        cache_key = self.get_cache_key(upstream_url)
        cached_tile = cache.get(cache_key)
        if cached_tile is not None:
            response = HttpResponse(
                cached_tile["content"], content_type=cached_tile["content_type"]
            )
            response["Cache-Control"] = "public, max-age=86400"
            return response

        request_headers = {
            "User-Agent": f"netbox-geoview/{__version__}",
            "Referer": request.build_absolute_uri(
                reverse("plugins:netbox_geoview:map")
            ),
        }

        try:
            with urlopen(
                Request(upstream_url, headers=request_headers), timeout=10
            ) as upstream_response:
                content = upstream_response.read()
                content_type = upstream_response.headers.get_content_type()
        except HTTPError as exc:
            if exc.code == 404:
                raise Http404 from exc
            return HttpResponse(status=502)
        except URLError:
            return HttpResponse(status=502)

        if not content_type.startswith("image/"):
            return HttpResponse(status=502)

        cache.set(
            cache_key,
            {"content": content, "content_type": content_type},
            timeout=86400,
        )
        response = HttpResponse(content, content_type=content_type)
        response["Cache-Control"] = "public, max-age=86400"
        return response
