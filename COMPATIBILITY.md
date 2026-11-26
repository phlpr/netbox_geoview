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

- `0.10.2` for NetBox `4.5.4` through `4.7.6`

Recommended branch model:

- `main` for the newest supported NetBox line
- additional `stable/<netbox-major>.<netbox-minor>` branches for older lines
  only when a maintained backport is required

## Release Matrix

| Plugin Release | Minimum NetBox | Maximum NetBox |
|---|---|---|
| 0.10.2 | 4.5.4 | 4.7.6 |

The 0.10.2 maximum of 4.7.6 is deliberately exact: later NetBox patch
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

GeoView 0.10.0 extends support to NetBox 4.7.4 and includes device-status filters,
native slug generation, tile revalidation and smoother map initialization. See
the [4.7.4 report](docs/validation/netbox-4.7.4.md) for the isolated environment,
release-package validation, browser checks and upstream upgrade notes.

GeoView 0.10.1 extends the tested maximum to NetBox 4.7.5 without a functional
plugin change. Its installed-wheel integration suite, focused upstream tests,
browser suites and isolated 4.7.4 database upgrade are recorded in the
[4.7.5 validation report](docs/validation/netbox-4.7.5.md). Older supported
patches were not newly revalidated by this compatibility-only release.

GeoView 0.10.2 extends the tested maximum to NetBox 4.7.6. No functional plugin
adaptation or migration is required. Its installed-wheel checks include real
read-only database sessions in maintenance mode, invalid dynamic selections,
native dashboard workflows and an isolated 4.7.5 upgrade comparison. See the
[4.7.6 validation report](docs/validation/netbox-4.7.6.md). Older supported
patches were not newly revalidated by this compatibility-only release.
