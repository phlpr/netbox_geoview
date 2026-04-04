PLUGINS = ["netbox_geoview"]

PLUGINS_CONFIG = {
    "netbox_geoview": {
        "start_latitude": 47.59397,
        "start_longitude": 14.12456,
        "start_zoom": 7,
        "min_zoom": 2,
        "max_zoom": 19,
        "default_tile_layer": "OpenStreetMap",
        "scroll_wheel_zoom": True,
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
    }
}
