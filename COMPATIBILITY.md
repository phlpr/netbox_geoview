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

Recommended maintenance lines:

- `0.6.x` for NetBox `4.5.4` through `4.6.x`
- older plugin releases remain available for installations that cannot upgrade

Recommended branch model:

- `main` for the newest supported NetBox line
- additional `stable/<netbox-major>.<netbox-minor>` branches for older lines
  only when a maintained backport is required

## Release Matrix

| Plugin Release | Minimum NetBox | Maximum NetBox | Notes |
|---|---|---|---|
| 0.6.x | 4.5.4 | 4.6.x | Current active line; tested with NetBox 4.6.8 |
| 0.5.x | 4.5.4 | 4.5.x | Previous release line |
| 0.4.x | 4.5.4 | 4.5.x | Previous release line |
| 0.3.x | 4.5.4 | 4.5.x | Previous release line |
| 0.2.x | 4.5.4 | 4.5.x | Previous release line |
| 0.1.x | 4.5.4 | 4.5.x | Previous release line |
