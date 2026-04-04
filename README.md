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
- `tile_provider_url`: upstream tile URL template with `{z}`, `{x}`, and `{y}`

## Requirements

- NetBox `4.5.5`
- Python `>=3.12`
- Installation inside the NetBox virtual environment
- Access to OpenStreetMap tiles for the map preview
