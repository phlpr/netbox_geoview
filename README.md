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

## Project Note

This is a personal project to see how far one can go with a practical NetBox plugin idea.

Most of the code was generated with Codex as a coding co-pilot, but maintenance responsibility stays with the developer (the human still carries the pager).

## Compatibility

| Plugin Release | NetBox |
|---|---|
| `0.1.x` | `4.5.5` to `4.5.x` |

## Installation

Install inside the NetBox virtual environment:

```bash
pip install netbox-geoview
```

Optional: install directly from a tagged GitHub source archive:

```bash
pip install https://github.com/phlpr/netbox_geoview/archive/refs/tags/v0.1.0.tar.gz
```

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
        "valhalla_url": "https://valhalla1.openstreetmap.de/route",
        "valhalla_timeout": 10,
        "valhalla_costing_options": ["auto", "bicycle", "pedestrian"],
        "valhalla_default_costing": "auto",
        "valhalla_request_defaults": {
            "alternates": 1,
            "directions_options": {
                "units": "kilometers",
            },
        },
        "valhalla_headers": {},
        "valhalla_query": {},
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
            "burgenland": {"color": "#f1c40f"},
            "karnten": {"color": "#e74c3c"},
            "niederosterreich": {"color": "#3498db"},
            "oberosterreich": {"color": "#2ecc71"},
            "salzburg": {"color": "#ff69b4"},
            "steiermark": {"color": "#16a085"},
            "tirol": {"color": "#9b59b6"},
            "vorarlberg": {"color": "#34495e"},
            "wien": {"color": "#f39c12"},
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
        ],
        "tile_provider_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    }
}
```

The same example is included in [configuration.example.py](./configuration.example.py).

Available settings:

- `start_latitude`: initial map latitude
- `start_longitude`: initial map longitude
- `start_zoom`: initial map zoom level
- `min_zoom`: minimum allowed zoom level
- `max_zoom`: maximum allowed zoom level
- `valhalla_url`: base URL of the Valhalla route endpoint
- `valhalla_timeout`: timeout in seconds for route requests
- `valhalla_costing_options`: route profile options shown in UI
- `valhalla_default_costing`: default route profile
- `valhalla_request_defaults`: additional request payload defaults
- `valhalla_headers`: optional HTTP headers for Valhalla requests
- `valhalla_query`: optional query string parameters for Valhalla requests
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

- NetBox `4.5.5` (or `4.5.x` compatible with this plugin release)
- Python `>=3.12`
- No additional Python runtime dependencies are required beyond NetBox's own environment
- Installation in the NetBox virtual environment (for example: `pip install <path-to-plugin>`)
- Plugin activation in `configuration.py`:
  - `PLUGINS = ["netbox_geoview"]`
  - `PLUGINS_CONFIG = {"netbox_geoview": {...}}`
- For MapTiler layers: valid API key (`query.key`)
- Optional for routing: reachable Valhalla endpoint (`valhalla_url`)

## Firewall / Network Allowlist

NetBox GeoView fetches external map and route data server-side. So the egress rules must be applied on the NetBox host (or its outbound proxy), not only on client browsers.

Required for default tile setup:

- `HTTPS/443` to `tile.openstreetmap.org`
- `HTTPS/443` to `tile.openstreetmap.de`
- `HTTPS/443` to `a.tile.openstreetmap.fr`

Required when using MapTiler layers:

- `HTTPS/443` to `api.maptiler.com`

Optional when routing is enabled (Valhalla):

- `HTTPS/443` to your configured Valhalla host from `valhalla_url`
- For the shipped example: `HTTPS/443` to `valhalla1.openstreetmap.de`

If your environment uses an explicit outbound proxy, make sure NetBox can reach these hosts through that proxy and that TLS inspection does not break certificate validation.
