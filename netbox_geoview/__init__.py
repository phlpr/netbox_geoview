from .version import NETBOX_MAX_VERSION, NETBOX_MIN_VERSION, __version__

try:
    from django.utils.translation import gettext_lazy as _
    from netbox.plugins import PluginConfig
except ModuleNotFoundError:
    # Allow importing utility submodules (for unit tests) without a full
    # Django/NetBox runtime available.
    config = None
else:
    class NetBoxGeoViewConfig(PluginConfig):
        name = "netbox_geoview"
        verbose_name = _("Geo-View")
        description = _("Geospatial view with map and filter tabs")
        version = __version__
        author = "Codex"
        base_url = "geoview"
        min_version = NETBOX_MIN_VERSION
        max_version = NETBOX_MAX_VERSION
        default_settings = {
            "start_latitude": 20.0,
            "start_longitude": 0.0,
            "start_zoom": 2,
            "min_zoom": 2,
            "max_zoom": 19,
            "default_tile_layer": "OpenStreetMap",
            "scroll_wheel_zoom": True,
            "site_marker": {
                "color": "#f1c40f",
                "symbol": "",
                "icon_url": "",
                "icon_size": [28, 40],
                "icon_anchor": [14, 40],
                "popup_anchor": [0, -34],
            },
            "site_group_markers": {},
            "tile_layers": [
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
            ],
            "tile_provider_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "map_center_lat": 20.0,
            "map_center_lon": 0.0,
            "map_zoom": 2,
            "tile_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        }


    config = NetBoxGeoViewConfig
