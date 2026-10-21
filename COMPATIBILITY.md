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

- `0.9.0` for NetBox `4.5.4` through `4.7.3`

Recommended branch model:

- `main` for the newest supported NetBox line
- additional `stable/<netbox-major>.<netbox-minor>` branches for older lines
  only when a maintained backport is required

## Release Matrix

| Plugin Release | Minimum NetBox | Maximum NetBox |
|---|---|---|
| 0.9.0 | 4.5.4 | 4.7.3 |

The 0.9.0 maximum of 4.7.3 is deliberately exact: later NetBox patch
releases still need validation.

See [testing details](TESTING.md) for validation reports and test instructions.

## Feature validation

Saved filters and dashboard widgets were validated on NetBox 4.5.10, 4.6.10 and 4.7.2 on
2026-10-15. Each target passed its integration suite and nine dashboard browser
scenarios. See the [feature validation report](docs/validation/saved-filters-widgets.md).
GeoView 0.9.0 includes these features, device-role filters and configurable role
colors/markers. Their focused tests also passed on 4.5.10 and 4.6.10; the complete
94-test integration suite passed on 4.7.2 and 4.7.3. NetBox 4.7.3 additionally
passed 32 browser checks and nine targeted upstream regressions. See the
[4.7.3 report](docs/validation/netbox-4.7.3.md),
[role-filter report](docs/validation/device-role-filter.md) and
[role-marker report](docs/validation/device-role-markers.md).
These checks do not newly validate every older patch within the supported range.
