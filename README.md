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

## Requirements

- NetBox `4.5.5`
- Python `>=3.12`
- Installation inside the NetBox virtual environment
- Access to OpenStreetMap tiles for the map preview
