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

- the development checkout extends support through NetBox `4.7.1`;
  see the [NetBox 4.7.1 validation report](docs/validation/netbox-4.7.1.md).
- published `0.8.0` for NetBox `4.5.4` through `4.7.0`;
  see the [NetBox 4.7.0 validation report](docs/validation/netbox-4.7.0.md).
- `0.7.x` for NetBox `4.5.4` through `4.6.x`
- older plugin releases remain available for installations that cannot upgrade

Recommended branch model:

- `main` for the newest supported NetBox line
- additional `stable/<netbox-major>.<netbox-minor>` branches for older lines
  only when a maintained backport is required

## Release Matrix

| Plugin Release | Minimum NetBox | Maximum NetBox | Notes |
|---|---|---|---|
| Development (unreleased) | 4.5.4 | 4.7.1 | Locally tested with NetBox 4.7.1 / Django 6.1.1 |
| 0.8.0 | 4.5.4 | 4.7.0 | Published release; locally tested with NetBox 4.7.0 / Django 6.1 |
| 0.7.x | 4.5.4 | 4.6.x | Previous release line; tested with NetBox 4.6.8 |
| 0.6.x | 4.5.4 | 4.6.x | Previous release line |
| 0.5.x | 4.5.4 | 4.5.x | Previous release line |
| 0.4.x | 4.5.4 | 4.5.x | Previous release line |
| 0.3.x | 4.5.4 | 4.5.x | Previous release line |
| 0.2.x | 4.5.4 | 4.5.x | Previous release line |
| 0.1.x | 4.5.4 | 4.5.x | Previous release line |

The development maximum of 4.7.1 is deliberately exact: later NetBox patch
releases still need validation. The published 0.8.0 package retains its 4.7.0
maximum; 0.7.0 retains its original 4.6.99 maximum. A new plugin release is
required to distribute the 4.7.1 compatibility change through PyPI.
Older supported versions were not re-tested during the 4.7.1 validation.
