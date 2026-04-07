import json
from datetime import date, datetime
from hashlib import sha256
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.contrib import messages
from core.models import ObjectType
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from dcim.models import Device, Site
from extras.models import SavedFilter
from netbox.plugins import get_plugin_config

from .forms import (
    DEVICE_FILTER_FIELDS,
    SITE_FILTER_FIELDS,
    GeoViewFilterForm,
    get_saved_filter_models,
)
from .polyline import decode_polyline
from .version import __version__


DEFAULT_TILE_LAYERS = [
    {
        "name": "OpenStreetMap",
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "&copy; OpenStreetMap contributors",
    },
    {
        "name": "OpenStreetMap DE",
        "url": "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
        "attribution": "&copy; OpenStreetMap contributors",
    },
    {
        "name": "OpenStreetMap HOT",
        "url": "https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
        "attribution": "&copy; OpenStreetMap contributors, Humanitarian OpenStreetMap Team",
    },
]

DEFAULT_SITE_MARKER = {
    "color": "#f1c40f",
    "symbol": "",
    "icon_url": "",
    "icon_size": [28, 40],
    "icon_anchor": [14, 40],
    "popup_anchor": [0, -34],
}

DEFAULT_VALHALLA_COSTING_OPTIONS = ["auto", "bicycle", "pedestrian"]

SUPPORTED_LOOKUP_OPERATORS = {"exact", "n"}
FIELD_OPERATOR_NAMES = (
    "tag",
    "region",
    "site_group",
    "site",
    "manufacturer",
    "device_type",
    "platform",
    "tenant_group",
    "tenant",
    "owner_group",
    "owner",
    "device",
)

DEFAULT_POPUP_SECTIONS = {
    "site": [
        {
            "title": "Core",
            "mode": "table",
            "fields": [
                "id",
                "name",
                "slug",
                "status",
                "region",
                "group",
                "tenant",
                "facility",
                "time_zone",
                "description",
                "physical_address",
                "shipping_address",
                "latitude",
                "longitude",
                "comments",
                "created",
                "last_updated",
            ],
        },
        {
            "title": "Counts",
            "mode": "table",
            "fields": [
                "circuit_count",
                "device_count",
                "prefix_count",
                "rack_count",
                "virtualmachine_count",
                "vlan_count",
            ],
        },
        {"title": "ASNs", "mode": "list", "field": "asns"},
        {"title": "Tags", "mode": "list", "field": "tags"},
        {"title": "Custom Fields", "mode": "table", "field": "custom_fields"},
    ],
    "device": [
        {
            "title": "Core",
            "mode": "table",
            "fields": [
                "id",
                "name",
                "status",
                "site",
                "role",
                "device_type",
                "platform",
                "tenant",
                "serial",
                "asset_tag",
                "latitude",
                "longitude",
                "created",
                "last_updated",
            ],
        },
        {"title": "Tags", "mode": "list", "field": "tags"},
        {"title": "Custom Fields", "mode": "table", "field": "custom_fields"},
    ],
}


def apply_saved_filter_parameters(data):
    if not data or ("filter" not in data and "filter_id" not in data):
        return data
    data = data.copy()
    saved_filters = SavedFilter.objects.filter(
        Q(slug__in=data.getlist("filter")) | Q(pk__in=data.getlist("filter_id"))
    )
    for saved_filter in saved_filters:
        for key, value in saved_filter.parameters.items():
            values = value if isinstance(value, (list, tuple)) else [value]
            if key in data:
                for entry in values:
                    data.appendlist(key, entry)
            else:
                data.setlist(key, values)
    return data


class GeoViewConfigMixin:
    plugin_name = "netbox_geoview"

    def get_plugin_settings(self):
        return getattr(settings, "PLUGINS_CONFIG", {}).get(self.plugin_name, {})

    def get_setting(self, *keys):
        plugin_settings = self.get_plugin_settings()
        for key in keys:
            if key in plugin_settings:
                return plugin_settings[key]
        for key in keys:
            value = get_plugin_config(self.plugin_name, key)
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

    def get_tile_layer_configs(self):
        configured_layers = self.get_setting("tile_layers")
        layers = configured_layers if configured_layers else DEFAULT_TILE_LAYERS
        min_zoom, max_zoom = self.get_zoom_bounds()
        normalized_layers = []
        used_ids = set()

        for index, layer in enumerate(layers, start=1):
            if not isinstance(layer, dict):
                continue
            name = str(layer.get("name") or f"Layer {index}").strip()
            url = str(layer.get("url") or "").strip()
            if not url:
                continue
            query = layer.get("query") if isinstance(layer.get("query"), dict) else {}
            headers = (
                layer.get("headers") if isinstance(layer.get("headers"), dict) else {}
            )
            layer_id = slugify(str(layer.get("id") or name)) or f"layer-{index}"
            suffix = 2
            while layer_id in used_ids:
                layer_id = f"{layer_id}-{suffix}"
                suffix += 1
            used_ids.add(layer_id)
            layer_min_zoom = max(min_zoom, min(max_zoom, int(layer.get("min_zoom", min_zoom))))
            layer_max_zoom = max(
                layer_min_zoom, min(max_zoom, int(layer.get("max_zoom", max_zoom)))
            )
            normalized_layers.append(
                {
                    "id": layer_id,
                    "name": name,
                    "url": url,
                    "attribution": str(layer.get("attribution") or ""),
                    "min_zoom": layer_min_zoom,
                    "max_zoom": layer_max_zoom,
                    "query": {str(key): str(value) for key, value in query.items()},
                    "headers": {str(key): str(value) for key, value in headers.items()},
                }
            )

        if normalized_layers:
            return normalized_layers

        fallback = DEFAULT_TILE_LAYERS[0].copy()
        fallback["id"] = "openstreetmap"
        fallback["min_zoom"] = min_zoom
        fallback["max_zoom"] = max_zoom
        fallback["query"] = {}
        fallback["headers"] = {}
        return [fallback]

    def get_default_tile_layer_id(self, layers):
        desired = str(self.get_setting("default_tile_layer") or "").strip().lower()
        if desired:
            for layer in layers:
                if desired in {layer["id"].lower(), layer["name"].lower()}:
                    return layer["id"]
        return layers[0]["id"]

    def get_scroll_wheel_zoom(self):
        value = self.get_setting("scroll_wheel_zoom")
        if value is None:
            return True
        return bool(value)

    def get_valhalla_url(self):
        value = str(self.get_setting("valhalla_url") or "").strip()
        if not value:
            return ""
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        return value

    def get_valhalla_timeout(self):
        try:
            timeout = float(self.get_setting("valhalla_timeout") or 10)
        except (TypeError, ValueError):
            timeout = 10
        return max(1.0, min(timeout, 60.0))

    def get_valhalla_query(self):
        query = self.get_setting("valhalla_query")
        if not isinstance(query, dict):
            return {}
        return {str(key): str(value) for key, value in query.items()}

    def get_valhalla_headers(self):
        headers = self.get_setting("valhalla_headers")
        if not isinstance(headers, dict):
            return {}
        return {str(key): str(value) for key, value in headers.items()}

    def get_valhalla_request_defaults(self):
        request_defaults = self.get_setting("valhalla_request_defaults")
        if not isinstance(request_defaults, dict):
            return {}
        return request_defaults.copy()

    def get_valhalla_costing_options(self):
        configured = self.get_setting("valhalla_costing_options")
        options = []
        if isinstance(configured, (list, tuple)):
            for option in configured:
                value = str(option or "").strip().lower()
                if value and value not in options:
                    options.append(value)
        if options:
            return options
        return DEFAULT_VALHALLA_COSTING_OPTIONS.copy()

    def get_valhalla_default_costing(self):
        desired = str(self.get_setting("valhalla_default_costing") or "").strip().lower()
        options = self.get_valhalla_costing_options()
        if desired in options:
            return desired
        return options[0]

    def get_routing_config(self):
        valhalla_url = self.get_valhalla_url()
        costing_options = self.get_valhalla_costing_options()
        costing_labels = {
            "auto": _("Car"),
            "bicycle": _("Bicycle"),
            "pedestrian": _("Walking"),
            "motorcycle": _("Motorcycle"),
            "bus": _("Bus"),
            "truck": _("Truck"),
            "taxi": _("Taxi"),
        }
        return {
            "enabled": bool(valhalla_url),
            "endpoint": reverse("plugins:netbox_geoview:route"),
            "costing_options": costing_options,
            "default_costing": self.get_valhalla_default_costing(),
            "costing_labels": {
                option: costing_labels.get(option, option.title())
                for option in costing_options
            },
        }

    def normalize_marker_style(self, marker_style, fallback=None):
        base = dict(fallback or DEFAULT_SITE_MARKER)
        if isinstance(marker_style, dict):
            for key in ("color", "symbol", "icon_url"):
                if key in marker_style:
                    base[key] = str(marker_style[key] or "")
            for key in ("icon_size", "icon_anchor", "popup_anchor"):
                value = marker_style.get(key)
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    base[key] = [int(value[0]), int(value[1])]
        return base

    def get_site_marker_style(self, site_group):
        default_style = self.normalize_marker_style(self.get_setting("site_marker"))
        configured_group_styles = self.get_setting("site_group_markers")
        if not isinstance(configured_group_styles, dict) or site_group is None:
            return default_style

        candidates = [str(site_group.name).strip().lower()]
        if getattr(site_group, "slug", None):
            candidates.append(str(site_group.slug).strip().lower())

        for key, style in configured_group_styles.items():
            if str(key).strip().lower() in candidates:
                return self.normalize_marker_style(style, default_style)

        return default_style

    def stringify_popup_value(self, value):
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat(sep=" ", timespec="seconds")
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def get_related_count(self, obj, relation_names):
        for relation_name in relation_names:
            manager = getattr(obj, relation_name, None)
            if manager is None or not hasattr(manager, "count"):
                continue
            try:
                return manager.count()
            except Exception:
                continue
        return 0

    def get_related_values(self, obj, relation_names):
        for relation_name in relation_names:
            manager = getattr(obj, relation_name, None)
            if manager is None or not hasattr(manager, "all"):
                continue
            try:
                values = []
                for item in manager.all():
                    values.append(getattr(item, "name", None) or str(item))
                return values
            except Exception:
                continue
        return []

    def normalize_custom_fields(self, obj):
        data = getattr(obj, "custom_field_data", None)
        if not isinstance(data, dict):
            return {}
        normalized = {}
        for key, value in data.items():
            if isinstance(value, (list, tuple)):
                normalized[str(key)] = ", ".join(
                    self.stringify_popup_value(entry) for entry in value
                )
            else:
                normalized[str(key)] = self.stringify_popup_value(value)
        return normalized

    def get_site_popup_values(self, site):
        return {
            "id": site.pk,
            "name": site.name,
            "slug": site.slug,
            "status": site.get_status_display(),
            "region": site.region.name if site.region else "",
            "group": site.group.name if site.group else "",
            "tenant": site.tenant.name if site.tenant else "",
            "facility": site.facility or "",
            "time_zone": site.time_zone or "",
            "description": site.description or "",
            "physical_address": site.physical_address or "",
            "shipping_address": site.shipping_address or "",
            "latitude": site.latitude,
            "longitude": site.longitude,
            "comments": site.comments or "",
            "created": site.created,
            "last_updated": site.last_updated,
            "circuit_count": self.get_related_count(site, ("circuits",)),
            "device_count": self.get_related_count(site, ("devices",)),
            "prefix_count": self.get_related_count(site, ("prefixes",)),
            "rack_count": self.get_related_count(site, ("racks",)),
            "virtualmachine_count": self.get_related_count(
                site, ("virtual_machines", "virtualmachines")
            ),
            "vlan_count": self.get_related_count(site, ("vlans",)),
            "asns": self.get_related_values(site, ("asns",)),
            "tags": [tag.name for tag in site.tags.all()],
            "custom_fields": self.normalize_custom_fields(site),
        }

    def get_device_popup_values(self, device):
        return {
            "id": device.pk,
            "name": device.name,
            "status": device.get_status_display(),
            "site": device.site.name if device.site else "",
            "role": device.role.name if device.role else "",
            "device_type": device.device_type.model if device.device_type else "",
            "platform": device.platform.name if device.platform else "",
            "tenant": device.tenant.name if device.tenant else "",
            "serial": device.serial or "",
            "asset_tag": device.asset_tag or "",
            "latitude": device.latitude
            if device.latitude is not None
            else (device.site.latitude if device.site else None),
            "longitude": device.longitude
            if device.longitude is not None
            else (device.site.longitude if device.site else None),
            "created": device.created,
            "last_updated": device.last_updated,
            "tags": [tag.name for tag in device.tags.all()],
            "custom_fields": self.normalize_custom_fields(device),
        }

    def normalize_popup_sections(self, object_type):
        configured = self.get_setting("popup_sections")
        if (
            isinstance(configured, dict)
            and isinstance(configured.get(object_type), list)
            and configured.get(object_type)
        ):
            return configured.get(object_type)
        return DEFAULT_POPUP_SECTIONS.get(object_type, [])

    def render_popup_sections(self, object_type, values):
        sections = []
        for section in self.normalize_popup_sections(object_type):
            if not isinstance(section, dict):
                continue
            title = self.stringify_popup_value(section.get("title") or "").strip()
            if not title:
                continue
            mode = self.stringify_popup_value(section.get("mode") or "table").lower()
            if mode == "table":
                rows = []
                fields = section.get("fields") or []
                if isinstance(fields, list):
                    for item in fields:
                        if isinstance(item, dict):
                            key = self.stringify_popup_value(item.get("key") or "")
                            label = self.stringify_popup_value(
                                item.get("label") or key
                            )
                        else:
                            key = self.stringify_popup_value(item)
                            label = key
                        if not key:
                            continue
                        value = values.get(key)
                        if isinstance(value, dict):
                            rows.extend(
                                [
                                    [self.stringify_popup_value(k), self.stringify_popup_value(v)]
                                    for k, v in value.items()
                                ]
                            )
                        else:
                            rows.append([label, self.stringify_popup_value(value)])
                single_field = self.stringify_popup_value(section.get("field") or "")
                if single_field:
                    value = values.get(single_field)
                    if isinstance(value, dict):
                        rows = [
                            [self.stringify_popup_value(k), self.stringify_popup_value(v)]
                            for k, v in value.items()
                        ]
                    elif value is not None:
                        rows = [[single_field, self.stringify_popup_value(value)]]
                sections.append({"title": title, "mode": "table", "rows": rows})
            elif mode == "list":
                field_name = self.stringify_popup_value(section.get("field") or "")
                values_list = values.get(field_name, [])
                if not isinstance(values_list, list):
                    values_list = [values_list] if values_list else []
                sections.append(
                    {
                        "title": title,
                        "mode": "list",
                        "items": [self.stringify_popup_value(item) for item in values_list],
                    }
                )
        return sections


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
        data = apply_saved_filter_parameters(self.request.GET or None)
        form = GeoViewFilterForm(data=data)
        if form.is_bound:
            form.is_valid()
        else:
            form.cleaned_data = {}
        return form

    def get_cleaned_data(self, form):
        if form.is_valid():
            return form.cleaned_data
        return {}

    def get_map_state(self):
        return self.get_initial_values()

    def get_filter_operators(self):
        operators = {}
        for field_name in FIELD_OPERATOR_NAMES:
            value = self.request.GET.get(f"{field_name}_op", "exact")
            operators[field_name] = value if value in SUPPORTED_LOOKUP_OPERATORS else "exact"
        return operators

    def has_site_filters(self, cleaned_data):
        return any(cleaned_data.get(field_name) for field_name in SITE_FILTER_FIELDS)

    def has_device_filters(self, cleaned_data):
        return any(cleaned_data.get(field_name) for field_name in DEVICE_FILTER_FIELDS)

    def apply_inclusion_filter(self, queryset, field_name, values, operator):
        if not values:
            return queryset
        if operator == "n":
            return queryset.exclude(**{f"{field_name}__in": values})
        return queryset.filter(**{f"{field_name}__in": values})

    def get_filtered_sites(self, cleaned_data, operators):
        if not self.has_site_filters(cleaned_data):
            return Site.objects.none()
        queryset = Site.objects.select_related("group", "region", "tenant").prefetch_related(
            "tags"
        ).order_by("name")
        queryset = self.apply_inclusion_filter(
            queryset, "region", cleaned_data.get("region"), operators["region"]
        )
        queryset = self.apply_inclusion_filter(
            queryset, "group", cleaned_data.get("site_group"), operators["site_group"]
        )
        queryset = self.apply_inclusion_filter(
            queryset, "pk", cleaned_data.get("site"), operators["site"]
        )
        return queryset.distinct()

    def get_filtered_devices(self, cleaned_data, operators):
        if not self.has_device_filters(cleaned_data):
            return Device.objects.none()
        queryset = Device.objects.select_related(
            "site__group",
            "site__region",
            "site__tenant",
            "device_type__manufacturer",
            "platform",
            "role",
            "tenant__group",
            "owner__group",
        ).prefetch_related("tags").order_by("name")
        search_query = cleaned_data.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(serial__icontains=search_query)
                | Q(asset_tag__icontains=search_query)
                | Q(site__name__icontains=search_query)
                | Q(device_type__model__icontains=search_query)
                | Q(device_type__manufacturer__name__icontains=search_query)
            )
        selected_tags = cleaned_data.get("tag") or []
        if selected_tags:
            include_untagged = settings.FILTERS_NULL_CHOICE_VALUE in selected_tags
            required_tags = [
                tag for tag in selected_tags if tag != settings.FILTERS_NULL_CHOICE_VALUE
            ]
            if operators["tag"] == "n":
                if include_untagged:
                    queryset = queryset.exclude(tags__isnull=True)
                for tag_slug in required_tags:
                    queryset = queryset.exclude(tags__slug=tag_slug)
            elif include_untagged and required_tags:
                tagged_queryset = queryset
                for tag_slug in required_tags:
                    tagged_queryset = tagged_queryset.filter(tags__slug=tag_slug)
                queryset = queryset.filter(
                    Q(tags__isnull=True) | Q(pk__in=tagged_queryset.values("pk"))
                )
            elif include_untagged:
                queryset = queryset.filter(tags__isnull=True)
            elif required_tags:
                for tag_slug in required_tags:
                    queryset = queryset.filter(tags__slug=tag_slug)

        queryset = self.apply_inclusion_filter(
            queryset,
            "device_type__manufacturer",
            cleaned_data.get("manufacturer"),
            operators["manufacturer"],
        )
        queryset = self.apply_inclusion_filter(
            queryset, "device_type", cleaned_data.get("device_type"), operators["device_type"]
        )
        queryset = self.apply_inclusion_filter(
            queryset, "platform", cleaned_data.get("platform"), operators["platform"]
        )
        queryset = self.apply_inclusion_filter(
            queryset, "tenant__group", cleaned_data.get("tenant_group"), operators["tenant_group"]
        )
        queryset = self.apply_inclusion_filter(
            queryset, "tenant", cleaned_data.get("tenant"), operators["tenant"]
        )
        queryset = self.apply_inclusion_filter(
            queryset, "owner__group", cleaned_data.get("owner_group"), operators["owner_group"]
        )
        queryset = self.apply_inclusion_filter(
            queryset, "owner", cleaned_data.get("owner"), operators["owner"]
        )
        queryset = self.apply_inclusion_filter(
            queryset, "pk", cleaned_data.get("device"), operators["device"]
        )
        return queryset.distinct()

    def get_device_coordinates(self, device):
        if device.latitude is not None and device.longitude is not None:
            return float(device.latitude), float(device.longitude)
        if (
            device.site is not None
            and device.site.latitude is not None
            and device.site.longitude is not None
        ):
            return float(device.site.latitude), float(device.site.longitude)
        return None

    def build_selection_groups(self, cleaned_data, operators):
        groups = []
        search_query = cleaned_data.get("q")
        if search_query:
            groups.append({"label": _("Search"), "entries": [search_query]})
        tags = cleaned_data.get("tag")
        if tags:
            groups.append(
                {
                    "label": _("Tags"),
                    "entries": [str(tag) for tag in tags],
                    "operator": operators["tag"],
                }
            )
        field_specs = (
            ("region", _("Region")),
            ("site_group", _("Site group")),
            ("site", _("Site")),
            ("manufacturer", _("Manufacturer")),
            ("device_type", _("Model")),
            ("platform", _("Operating system")),
            ("tenant_group", _("Tenant group")),
            ("tenant", _("Tenant")),
            ("owner_group", _("Owner group")),
            ("owner", _("Owner")),
            ("device", _("Device")),
        )
        for field_name, label in field_specs:
            values = cleaned_data.get(field_name)
            if not values:
                continue
            groups.append(
                {
                    "label": label,
                    "entries": [getattr(obj, "name", None) or str(obj) for obj in values],
                    "operator": operators.get(field_name, "exact"),
                }
            )
        if groups:
            return groups
        return []

    def get_active_filter_count(self, cleaned_data):
        count = 0
        if cleaned_data.get("q"):
            count += 1
        if cleaned_data.get("tag"):
            count += 1
        for key in (
            "region",
            "site_group",
            "site",
            "manufacturer",
            "device_type",
            "platform",
            "tenant_group",
            "tenant",
            "owner_group",
            "owner",
            "device",
        ):
            if cleaned_data.get(key):
                count += 1
        return count

    def build_tab_url(self, view_name):
        base_url = reverse(view_name)
        query_string = self.request.GET.urlencode()
        if query_string:
            return f"{base_url}?{query_string}"
        return base_url

    def build_site_markers(self, sites, devices):
        markers = []
        for site in sites:
            if site.latitude is None or site.longitude is None:
                continue
            popup_values = self.get_site_popup_values(site)
            markers.append(
                {
                    "name": site.name,
                    "group_name": site.group.name if site.group else "",
                    "object_type": "site",
                    "netbox_url": self.request.build_absolute_uri(site.get_absolute_url()),
                    "latitude": float(site.latitude),
                    "longitude": float(site.longitude),
                    "marker_style": self.get_site_marker_style(site.group),
                    "popup_sections": self.render_popup_sections("site", popup_values),
                }
            )
        for device in devices:
            coordinates = self.get_device_coordinates(device)
            if coordinates is None:
                continue
            latitude, longitude = coordinates
            site = device.site
            popup_values = self.get_device_popup_values(device)
            markers.append(
                {
                    "name": device.name or str(device),
                    "group_name": site.name if site else "",
                    "object_type": "device",
                    "netbox_url": self.request.build_absolute_uri(device.get_absolute_url()),
                    "latitude": latitude,
                    "longitude": longitude,
                    "marker_style": self.get_site_marker_style(
                        site.group if site and site.group else None
                    ),
                    "popup_sections": self.render_popup_sections("device", popup_values),
                }
            )
        return markers

    def get_map_config(self, map_state, sites, devices, has_active_filters):
        tile_layers = self.get_tile_layer_configs()
        public_tile_layers = [
            {
                "id": layer["id"],
                "name": layer["name"],
                "attribution": layer["attribution"],
                "min_zoom": layer["min_zoom"],
                "max_zoom": layer["max_zoom"],
            }
            for layer in tile_layers
        ]
        routing_config = self.get_routing_config()
        return {
            "lat": map_state["lat"],
            "lon": map_state["lon"],
            "zoom": map_state["zoom"],
            "min_zoom": self.get_zoom_bounds()[0],
            "max_zoom": self.get_zoom_bounds()[1],
            "scroll_wheel_zoom": self.get_scroll_wheel_zoom(),
            "default_tile_layer_id": self.get_default_tile_layer_id(tile_layers),
            "routing": routing_config,
            "ui": {
                "netbox": _("NetBox"),
                "open_google_maps": _("Open in Google Maps"),
                "set_start": _("Set as start"),
                "set_end": _("Set as end"),
                "route_error": _("Route could not be calculated."),
                "distance": _("Distance"),
                "duration": _("Duration"),
                "mode": _("Mode"),
                "alternative": _("Alternative"),
                "calculating_route": _("Calculating route..."),
            },
            "tile_proxy_url_template": reverse(
                "plugins:netbox_geoview:tile",
                kwargs={"layer_id": "__layer__", "z": 0, "x": 0, "y": 0},
            ).replace("/0/0/0.png", "/{z}/{x}/{y}.png"),
            "tile_layers": public_tile_layers,
            "site_markers": self.build_site_markers(sites, devices) if has_active_filters else [],
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_form()
        cleaned_data = self.get_cleaned_data(form)
        operators = self.get_filter_operators()
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
                    relation = _("does not have these tags") if operator == "n" else _("has these tags")
                else:
                    relation = _("is not") if operator == "n" else _("is")
                active_filter_badges.append(f'{group["label"]} {relation}: {entries}')

        save_filter_url = None
        if (
            has_active_filters
            and self.request.user.has_perm("extras.add_savedfilter")
            and "filter_id" not in self.request.GET
        ):
            object_type_ids = [
                ObjectType.objects.get_for_model(model).pk
                for model in get_saved_filter_models(cleaned_data)
            ]
            parameters = json.dumps(dict(self.request.GET.lists()))
            save_filter_query = urlencode(
                {
                    "object_types": object_type_ids,
                    "parameters": parameters,
                },
                doseq=True,
            )
            save_filter_url = (
                f'{reverse("extras:savedfilter_add")}?{save_filter_query}'
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
                "selection_groups": self.build_selection_groups(cleaned_data, operators),
                "selection_counts": {
                    "sites": filtered_sites.count(),
                    "devices": filtered_devices.count(),
                },
                "active_filter_count": self.get_active_filter_count(cleaned_data),
                "active_filter_badges": active_filter_badges,
                "save_filter_url": save_filter_url,
                "filter_ops": operators,
                "asset_version": f"{__version__}-routing-3",
                "routing_profiles": [
                    {
                        "value": option,
                        "label": routing_config["costing_labels"].get(option, option.title()),
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


class GeoViewApplyFiltersView(GeoViewConfigMixin, View):
    http_method_names = ["get"]

    def get(self, request):
        form = GeoViewFilterForm(data=apply_saved_filter_parameters(request.GET or None))
        form.is_valid()
        cleaned_data = form.cleaned_data if form.is_valid() else {}
        selected_devices = cleaned_data.get("device")
        if selected_devices:
            has_unmappable_device = any(
                (
                    device.latitude is None
                    or device.longitude is None
                )
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
                layer["url"].replace("{z}", str(z)).replace("{x}", str(x)).replace(
                    "{y}", str(y)
                )
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
            response["Cache-Control"] = "public, max-age=86400"
            return response

        request_headers = {
            "User-Agent": f"netbox-geoview/{__version__}",
            "Referer": request.build_absolute_uri(
                reverse("plugins:netbox_geoview:map")
            ),
        }
        request_headers.update(layer_headers)

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


class GeoViewRouteView(GeoViewConfigMixin, View):
    http_method_names = ["get"]

    def get_float_query_param(self, request, key, min_value, max_value):
        raw_value = request.GET.get(key)
        if raw_value is None:
            raise ValueError
        value = float(raw_value)
        if value < min_value or value > max_value:
            raise ValueError
        return value

    def parse_valhalla_error(self, response_data):
        if isinstance(response_data, dict):
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
        costing = str(request.GET.get("costing") or self.get_valhalla_default_costing()).lower()
        if costing not in costing_options:
            costing = self.get_valhalla_default_costing()

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
            with urlopen(
                Request(
                    valhalla_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=request_headers,
                    method="POST",
                ),
                timeout=self.get_valhalla_timeout(),
            ) as upstream_response:
                response_data = json.loads(upstream_response.read().decode("utf-8"))
        except HTTPError as exc:
            response_data = None
            try:
                response_data = json.loads(exc.read().decode("utf-8"))
            except Exception:
                response_data = None
            return JsonResponse(
                {
                    "success": False,
                    "error": self.parse_valhalla_error(response_data),
                },
                status=400 if exc.code < 500 else 502,
            )
        except (URLError, TimeoutError):
            return JsonResponse(
                {
                    "success": False,
                    "error": _("Routing service is unavailable."),
                },
                status=502,
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {
                    "success": False,
                    "error": _("Routing service returned an invalid response."),
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
        alternates_raw = response_data.get("alternates", []) if isinstance(response_data, dict) else []
        if isinstance(alternates_raw, list):
            for alternate in alternates_raw:
                alt_trip = alternate.get("trip") if isinstance(alternate, dict) else alternate
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
