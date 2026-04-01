# Compatibility Matrix

## Version Scheme

This plugin uses semantic versioning for plugin releases:

`MAJOR.MINOR.PATCH`

- `MAJOR` for breaking plugin changes
- `MINOR` for new backward-compatible features
- `PATCH` for bug fixes

NetBox compatibility is tracked separately through:

- `min_version` and `max_version` in `netbox_geoview/version.py`
- package dependency constraints in `pyproject.toml`
- this compatibility matrix

Recommended maintenance lines:

- `0.1.x` for NetBox `4.5.x`
- `0.0.x` for NetBox `3.7.x`
- older NetBox branches keep their own patch line if needed

Recommended branch model:

- `main` for the newest supported NetBox line
- `stable/4.5` for NetBox `4.5.x`
- `stable/3.7` for NetBox `3.7.x`
- additional `stable/<netbox-major>.<netbox-minor>` branches for older lines

## Release Matrix

| Plugin Release | Minimum NetBox | Maximum NetBox | Notes |
|---|---|---|---|
| 0.1.x | 4.5.5 | 4.5.x | Current active line |
| 0.0.x | 3.7.10 | 3.7.x | Reserved backport line |
