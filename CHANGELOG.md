# Changelog

All notable changes to NetBox GeoView are documented in this file. The project
uses semantic versioning for plugin releases.

## Unreleased

## 0.10.2 - 2026-11-26

### Compatibility

- Support NetBox 4.5.4 through exactly 4.7.6. Only the package version and
  maximum NetBox version change in runtime code; no functional adaptation,
  additional dependency or plugin migration is required. GeoView 0.10.1
  remains limited to NetBox 4.7.5.

### Tests

- Verify real read-only database sessions in NetBox 4.7.6: maps, choices and
  dashboards remain readable, saved-filter and widget writes are refused,
  writes resume after maintenance, and a default dashboard is not persisted.
- Check that invalid dynamic device selections render errors without exposing
  other map data and can be corrected successfully. These regressions are
  skipped on older NetBox versions without the corresponding upstream fixes.

### Documentation

- Update installation examples and the compatibility matrix. Record the
  installed-wheel, upstream and browser checks, isolated 4.7.5 database
  comparison and relevant upgrade notes in the 4.7.6 validation report.

## 0.10.1 - 2026-11-10

### Compatibility

- Support NetBox 4.5.4 through exactly 4.7.5 by raising only the maximum NetBox
  version. No functional plugin changes, new dependencies or plugin migrations
  are required. GeoView 0.10.0 remains limited to NetBox 4.7.4.
- Validate the installed release wheel against NetBox 4.7.5 and its pinned
  dependencies, including Django 6.1.3 and django-taggit 7.0.0. Add regressions
  for filtered/ordered device choices with narrow REST responses and live tag
  replacement across maps, device choices and saved widgets.

### Documentation

- Record integration, upstream and browser checks, the isolated 4.7.4 upgrade
  comparison, and relevant migration/SSO upgrade notes in the 4.7.5 report.
- Extend the browser save workflow with invalid-input recovery and synchronize
  manual slug entry with NetBox's blur-driven automatic generation.

## 0.10.0 - 2026-11-01

### Added

- Filter devices by one or more NetBox statuses, including custom choices and
  exclusion operators, across maps, dynamic device choices and saved widgets.

### Fixed

- Keep dashboard maps, selected base layers and loaded tiles when refreshing
  widget markers. Reuse browser-cached tile images through ETag revalidation on
  page reloads while checking permissions on each tile request.
- Initialize the final map viewport before requesting tiles, disable tile fading
  and reveal the initial map together after its tile load completes, with a
  timeout fallback for stalled requests.

### Changed

- Use NetBox's native slug field for saved filters, including automatic
  generation and preservation of manually entered slugs.
- Populate GitHub release notes from the matching dated changelog section and
  include a link to the previous version. Validate release notes before publishing
  to PyPI; missing, duplicate or empty entries stop the release workflow.

### Compatibility

- Support NetBox 4.5.4 through exactly 4.7.4. Validate the 4.7.4 dependency set,
  selectors, REST device choices, saved filters, tags with 64-bit object IDs,
  dashboard widgets and map rendering. No plugin migration is required.

## 0.9.0 - 2026-10-22

### Added

- Save, reload, update and copy GeoView filters using NetBox's existing SavedFilter
  model, including names, descriptions, ownership and sharing. Effective filter
  conditions are stored without nested filter references or map display settings.
- Add a native GeoView dashboard widget with a saved-filter selector, automatic
  marker bounds, manual refresh, popups and a link to the full map. Multiple widgets
  can share the same assets and resize independently.
- Filter devices by role, including or excluding descendant roles, with matching
  dynamic device choices, saved filters and dashboard results.
- Optionally use NetBox device-role colors with the Boolean `use_role_colors`
  setting (default `False`). Configure per-role colors, text symbols or custom
  images through `device_role_markers`; explicit role overrides take precedence.

### Fixed

- Resolve saved inclusion/exclusion operators together with filter values, and
  constrain device results by selected site/region/site-group conditions.
- Reject unavailable, incompatible, unsupported and circular saved filters instead
  of falling back to an unfiltered map. Explicit URL selections override saved values.
- Recheck filter and object permissions for widget data requests and send marker
  responses with private/no-store caching. Updating filters requires ownership (or
  a superuser) and NetBox's existing change permission; creating requires add permission.
- Initialize maps idempotently on page and HTMX loads, resize Leaflet maps with their
  containers, and clean up map instances when fragments are removed.
- Keep marker symbols upright and centered within the pin head.

### Compatibility

- Support NetBox 4.5.4 through exactly 4.7.3. The 4.7.3 compatibility check passed
  94 GeoView integration tests, nine focused upstream regressions and 32 browser
  checks. No plugin database migration is required.

### Documentation

- Document saved filters, dashboard widgets, device roles and marker configuration,
  compatibility validation, permissions and reproducible browser checks.

## 0.8.2 - 2026-10-01

### Compatibility

- Support NetBox 4.5.4 through 4.7.2 by raising the maximum supported version
  to exactly 4.7.2. No functional plugin changes or database migrations are
  required. GeoView 0.8.1 remains limited to NetBox 4.7.1.
- Validate NetBox 4.7.2 with 49 GeoView integration tests, 14 focused upstream
  regressions and 13 browser checks; see `docs/validation/netbox-4.7.2.md`.

### Documentation

- Show only the current release in the compatibility matrix and link the
  README installation instructions directly to the PyPI project.

## 0.8.1 - 2026-09-30

### Fixed

- Require login and either Site or Device view permission for the GeoView menu
  and all endpoints, including tiles and routing, even with `LOGIN_REQUIRED`
  disabled. Use existing NetBox permissions and retain object constraints;
  no new permission or database migration is required.
- Mark tile responses private and require revalidation so shared HTTP caches
  cannot bypass the access check. The internal tile cache remains enabled.

### Compatibility

- Validate NetBox 4.7.1 with Django 6.1.1 and Python 3.14.7 in an isolated local
  environment and raise the maximum supported NetBox version to exactly 4.7.1.
- Add regression coverage for Unicode device search, hierarchical filter choices
  after move/rename, device mapping after location changes, and multiselect
  custom-field popup values. No plugin model migration is required.
- Document the NetBox 4.7.1 hierarchy-restore warning and validation scope in
  `docs/validation/netbox-4.7.1.md`. GeoView 0.8.0 remains limited to NetBox 4.7.0;
  support for NetBox 4.7.1 starts with this release.

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
