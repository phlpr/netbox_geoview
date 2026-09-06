# Changelog

All notable changes to NetBox GeoView are documented in this file. The project
uses semantic versioning for plugin releases.

## 0.8.0 - 2026-09-06

### Compatibility

- Validate NetBox 4.7.0 with Django 6.1 and Python 3.14.7 locally, and raise the
  maximum supported NetBox version from 4.6.99 to 4.7.0.
- Add repeatable PostgreSQL integration tests and Playwright browser checks;
  see `TESTING.md` and `docs/validation/netbox-4.7.0.md` for scope and results.

### Fixed

- Apply NetBox's login requirement to all GeoView endpoints and respect object
  permissions in map queries and filter choices.
- Only expand enabled saved filters that the user can access and which are
  shared or belong to that user.
- Handle malformed saved-filter IDs with normal form validation instead of a
  server error; reject non-finite routing coordinates before contacting Valhalla.
- Wrap long active filter badges on narrow screens and remove the unused mobile
  grid row when the route panel is hidden.

## 0.7.0 - 2026-08-22

### Fixed

- Leaflet popups, tooltips, map controls, attribution, and GeoView panels now
  follow NetBox's light and dark themes using the supported Tabler CSS
  variables.

## 0.6.0 - 2026-08-22

### Added

- Support for NetBox 4.6.x, tested with NetBox 4.6.8.
- Reusable, idempotent development test data via
  `python manage.py seed_geoview_testdata`.
- Packaged JSON definitions for sites, nested locations, device types, roles,
  devices, and custom-field mappings.

### Changed

- The map viewport now includes active filter badges in its height calculation,
  preventing an unnecessary page scrollbar in NetBox.
- The example Valhalla configuration documents an identifying `X-Client-Id`
  header and clarifies public-demo versus production use.
- Package metadata now uses the SPDX `MIT` license expression, and release
  documentation is included in the source distribution.

### Compatibility

- Minimum NetBox version: 4.5.4.
- Maximum NetBox version: 4.6.x.
- Verified NetBox version: 4.6.8.

## 0.5.0

- Added route calculation and direct-distance features.

## 0.4.0

- Improved route handling and proxy-related behavior.
