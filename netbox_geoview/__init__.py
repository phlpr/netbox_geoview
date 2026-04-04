from django.utils.translation import gettext_lazy as _
from netbox.plugins import PluginConfig

from .version import NETBOX_MAX_VERSION, NETBOX_MIN_VERSION, __version__


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
        "map_center_lat": 20.0,
        "map_center_lon": 0.0,
        "map_zoom": 2,
        "tile_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    }


config = NetBoxGeoViewConfig
