# NetBox GeoView

NetBox GeoView is a NetBox plugin for displaying infrastructure in a map-oriented view.

The current skeleton provides two tabs:

- `Map`: primary view with an OpenStreetMap tile preview
- `Filter`: selection of devices, sites, locations, roles, and map parameters

## Versioning

The plugin uses Semantic Versioning in the format `MAJOR.MINOR.PATCH`.

- `MAJOR`: incompatible plugin changes
- `MINOR`: new backward-compatible features
- `PATCH`: bug fixes and small corrections

NetBox compatibility is managed separately through `min_version` and `max_version` in the plugin.

## Compatibility

| Plugin Release | NetBox |
|---|---|
| `0.1.x` | `4.5.5` to `4.5.x` |

## Configuration

Example plugin settings for `configuration.py`:

```python
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
        "site_marker": {
            "color": "#f1c40f",
            "symbol": "",
            "icon_url": "",
            "icon_size": [28, 40],
            "icon_anchor": [14, 40],
            "popup_anchor": [0, -34],
        },
        "site_group_markers": {
            "LOWG": {
                "color": "#2ecc71",
            },
            "LOWK": {
                "color": "#3498db",
            },
            "LOWL": {
                "color": "#e74c3c",
            },
            "LOWS": {
                "color": "#ff69b4",
            },
        },
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
```

The same example is included in [configuration.example.py](/D:/Programmierung/netbox_geoview/configuration.example.py).

Available settings:

- `start_latitude`: initial map latitude
- `start_longitude`: initial map longitude
- `start_zoom`: initial map zoom level
- `min_zoom`: minimum allowed zoom level
- `max_zoom`: maximum allowed zoom level
- `default_tile_layer`: default base layer name or ID
- `scroll_wheel_zoom`: enables zooming with the mouse wheel
- `site_marker`: default marker appearance for selected sites
- `site_group_markers`: marker overrides by site group name or slug
- `tile_layers`: list of available base layers
- `query`: optional query string parameters per layer, useful for API keys
- `headers`: optional HTTP headers per layer
- `tile_provider_url`: upstream tile URL template with `{z}`, `{x}`, and `{y}`

## Satellite Providers

Providers with official API-key-based access that fit this plugin well:

- `MapTiler Satellite`: simple raster tile API with API key in the request. Official docs: [MapTiler Cloud API](https://docs.maptiler.com/cloud/api/)
- `MapTiler Hybrid`: raster hybrid style with satellite imagery plus labels and borders, also usable with an API key. Inference from MapTiler's documented style family plus verified tile endpoint.
- `Mapbox Satellite`: raster tiles with access token authentication. Official docs: [Mapbox Tilesets Reference](https://docs.mapbox.com/data/tilesets/reference/mapbox-satellite/)
- `Esri World Imagery`: enterprise-capable imagery via ArcGIS location services and token-based authentication. Official docs: [ArcGIS service endpoints](https://developers.arcgis.com/documentation/mapping-and-location-services/service-endpoints/) and [Esri Leaflet basemap example](https://developers.arcgis.com/esri-leaflet/maps/raster-tile-basemaps/display-multiple-basemap-layers/)

Recommendation:

- `MapTiler Satellite` is the easiest fit for the current plugin because it follows a straightforward raster tile pattern with an API key.
- `Mapbox Satellite` also fits well and can be configured today with `query.access_token`.
- `Esri World Imagery` is a strong enterprise option, but its exact request pattern depends on the ArcGIS endpoint and token model you want to use.

## Requirements

- NetBox `4.5.5`
- Python `>=3.12`
- Installation inside the NetBox virtual environment
- Access to OpenStreetMap tiles for the map preview
