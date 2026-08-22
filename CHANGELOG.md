# Changelog

All notable changes to NetBox GeoView are documented in this file. The project
uses semantic versioning for plugin releases.

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
