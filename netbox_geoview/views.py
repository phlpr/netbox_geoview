from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from dcim.models import Device
from netbox.plugins import get_plugin_config

from .forms import GeoViewFilterForm


class GeoViewBaseView(TemplateView):
    active_tab = "map"

    def get_initial_values(self):
        return {
            "lat": get_plugin_config("netbox_geoview", "map_center_lat"),
            "lon": get_plugin_config("netbox_geoview", "map_center_lon"),
            "zoom": get_plugin_config("netbox_geoview", "map_zoom"),
            "limit": 250,
        }

    def get_form(self):
        data = self.request.GET or None
        return GeoViewFilterForm(data=data, initial=self.get_initial_values())

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
            "zoom": cleaned_data.get("zoom")
            if cleaned_data.get("zoom") is not None
            else initial["zoom"],
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
                "active_tab": self.active_tab,
                "filter_form": form,
                "map_state": map_state,
                "tile_url": get_plugin_config("netbox_geoview", "tile_url"),
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
                    "title": _("OpenStreetMap tile preview"),
                    "latitude": _("Latitude"),
                    "longitude": _("Longitude"),
                    "zoom": _("Zoom"),
                },
            }
        )
        return context


class GeoViewMapView(GeoViewBaseView):
    template_name = "netbox_geoview/map.html"
    active_tab = "map"


class GeoViewFilterView(GeoViewBaseView):
    template_name = "netbox_geoview/filter.html"
    active_tab = "filter"
