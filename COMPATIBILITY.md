# Compatibility Matrix

## Version Scheme

This plugin uses semantic versioning for plugin releases:

`MAJOR.MINOR.PATCH`

- `MAJOR` for breaking plugin changes
- `MINOR` for new backward-compatible features
- `PATCH` for bug fixes

NetBox compatibility is tracked separately through:

- `min_version` and `max_version` in `netbox_geoview/version.py`
- this compatibility matrix

Recommended release:

- `0.8.2` for NetBox `4.5.4` through `4.7.2`

Recommended branch model:

- `main` for the newest supported NetBox line
- additional `stable/<netbox-major>.<netbox-minor>` branches for older lines
  only when a maintained backport is required

## Release Matrix

| Plugin Release | Minimum NetBox | Maximum NetBox |
|---|---|---|
| 0.8.2 | 4.5.4 | 4.7.2 |

The 0.8.2 maximum of 4.7.2 is deliberately exact: later NetBox patch
releases still need validation.

See [testing details](TESTING.md) for validation reports and test instructions.
