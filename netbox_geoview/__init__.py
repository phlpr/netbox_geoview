from netbox.plugins import PluginConfig

from .version import NETBOX_MAX_VERSION, NETBOX_MIN_VERSION, __version__


class NetBoxGeoViewConfig(PluginConfig):
    name = "netbox_geoview"
    verbose_name = "NetBox GeoView"
    description = "Geo view skeleton with map and filter tabs"
    version = __version__
    author = "Codex"
    base_url = "geoview"
    min_version = NETBOX_MIN_VERSION
    max_version = NETBOX_MAX_VERSION
    default_settings = {
        "map_center_lat": 48.2082,
        "map_center_lon": 16.3738,
        "map_zoom": 6,
        "tile_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    }


config = NetBoxGeoViewConfig
