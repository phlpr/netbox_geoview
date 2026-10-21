"""Shared map configuration, queries and marker preparation for views and widgets."""

from datetime import date, datetime
from urllib.parse import urlparse

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext as _
from dcim.models import Device, Site
from netbox.plugins import get_plugin_config
from utilities.filters import TreeNodeMultipleChoiceFilter

from ..filters import DEVICE_FILTER_FIELDS, SITE_FILTER_FIELDS

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


class GeoViewMapService:
    def __init__(self, request=None, **kwargs):
        super().__init__(**kwargs)
        if request is not None:
            self.request = request

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
            layer_min_zoom = max(
                min_zoom, min(max_zoom, int(layer.get("min_zoom", min_zoom)))
            )
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
        desired = (
            str(self.get_setting("valhalla_default_costing") or "").strip().lower()
        )
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
                            label = self.stringify_popup_value(item.get("label") or key)
                        else:
                            key = self.stringify_popup_value(item)
                            label = key
                        if not key:
                            continue
                        value = values.get(key)
                        if isinstance(value, dict):
                            rows.extend(
                                [
                                    [
                                        self.stringify_popup_value(k),
                                        self.stringify_popup_value(v),
                                    ]
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
                            [
                                self.stringify_popup_value(k),
                                self.stringify_popup_value(v),
                            ]
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
                        "items": [
                            self.stringify_popup_value(item) for item in values_list
                        ],
                    }
                )
        return sections

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

    def apply_role_filter(self, queryset, roles, operator):
        if not roles:
            return queryset
        # Match NetBox's device filter, including descendants on both tree backends.
        return TreeNodeMultipleChoiceFilter(
            field_name="role", lookup_expr="in", exclude=operator == "n"
        ).filter(queryset, roles)

    def get_filtered_sites(self, cleaned_data, operators):
        if not self.has_site_filters(cleaned_data):
            return Site.objects.none()
        queryset = (
            Site.objects.restrict(self.request.user, "view")
            .select_related("group", "region", "tenant")
            .prefetch_related("tags")
            .order_by("name")
        )
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
        queryset = (
            Device.objects.restrict(self.request.user, "view")
            .select_related(
                "site__group",
                "site__region",
                "site__tenant",
                "device_type__manufacturer",
                "platform",
                "role",
                "tenant__group",
                "owner__group",
            )
            .prefetch_related("tags")
            .order_by("name")
        )
        if self.has_site_filters(cleaned_data):
            queryset = queryset.filter(
                site__in=self.get_filtered_sites(cleaned_data, operators)
            )
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
                tag
                for tag in selected_tags
                if tag != settings.FILTERS_NULL_CHOICE_VALUE
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
            queryset,
            "device_type",
            cleaned_data.get("device_type"),
            operators["device_type"],
        )
        queryset = self.apply_inclusion_filter(
            queryset, "platform", cleaned_data.get("platform"), operators["platform"]
        )
        queryset = self.apply_role_filter(
            queryset, cleaned_data.get("role"), operators["role"]
        )
        queryset = self.apply_inclusion_filter(
            queryset,
            "tenant__group",
            cleaned_data.get("tenant_group"),
            operators["tenant_group"],
        )
        queryset = self.apply_inclusion_filter(
            queryset, "tenant", cleaned_data.get("tenant"), operators["tenant"]
        )
        queryset = self.apply_inclusion_filter(
            queryset,
            "owner__group",
            cleaned_data.get("owner_group"),
            operators["owner_group"],
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
            ("role", _("Device roles")),
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
                    "entries": [
                        getattr(obj, "name", None) or str(obj) for obj in values
                    ],
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
            "role",
            "tenant_group",
            "tenant",
            "owner_group",
            "owner",
            "device",
        ):
            if cleaned_data.get(key):
                count += 1
        return count

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
                    "netbox_url": self.request.build_absolute_uri(
                        site.get_absolute_url()
                    ),
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
                    "netbox_url": self.request.build_absolute_uri(
                        device.get_absolute_url()
                    ),
                    "latitude": latitude,
                    "longitude": longitude,
                    "marker_style": self.get_site_marker_style(
                        site.group if site and site.group else None
                    ),
                    "popup_sections": self.render_popup_sections(
                        "device", popup_values
                    ),
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
                "close": _("Close"),
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
            "site_markers": self.build_site_markers(sites, devices)
            if has_active_filters
            else [],
        }
