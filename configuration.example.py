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
            {
                "name": "MapTiler Satellite",
                "url": "https://api.maptiler.com/maps/satellite/{z}/{x}/{y}.jpg",
                "attribution": "&copy; MapTiler",
                "query": {
                    "key": "YOUR_MAPTILER_API_KEY",
                },
            },
            {
                "name": "MapTiler Hybrid",
                "url": "https://api.maptiler.com/maps/hybrid/{z}/{x}/{y}.png",
                "attribution": "&copy; MapTiler",
                "query": {
                    "key": "YOUR_MAPTILER_API_KEY",
                },
            },
            {
                "name": "Mapbox Satellite",
                "url": "https://api.mapbox.com/v4/mapbox.satellite/{z}/{x}/{y}.jpg90",
                "attribution": "&copy; Mapbox",
                "query": {
                    "access_token": "YOUR_MAPBOX_ACCESS_TOKEN",
                },
            },
        ],
        "tile_provider_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    }
}
