# NetBox 4.7.3 compatibility check — 2026-10-22

GeoView works on NetBox 4.7.3 after raising only `NETBOX_MAX_VERSION` from
`4.7.2` to `4.7.3` in disposable plugin copies. Both the published 0.8.2 code
and the development checkout at `75ec937` passed their integration suites.
No functional plugin changes, new dependencies or plugin migrations were needed.

**Unchanged GeoView 0.8.2 and the current checkout do not load on NetBox 4.7.3.**
Their maximum supported version is still 4.7.2. The baseline check reproduced
NetBox's version warning and asserted that GeoView was absent from Django's app
registry. Updating that compatibility limit is necessary to enable the plugin.
This validation changes the limit only in test copies; repository and release
compatibility metadata remain 4.5.4–4.7.2.

## Environment

| Component | Version / setup |
|---|---|
| NetBox | Official `v4.7.3`, commit `3cd2c1d6469caed6c50e80eddd4cde863e0e2cf5` |
| Development plugin | `75ec937`, copied with `git archive`; only its maximum NetBox version changed |
| Release plugin | Published 0.8.2 wheel extracted into a separate importable copy; only its maximum NetBox version changed |
| Python / Django / django-filter | 3.14.7 / 6.1.2 / 26.2 |
| Dependencies | Separate virtual environment with the exact 4.7.3 runtime and testing requirements; `pip check` passed |
| PostgreSQL / Redis | 16.15 / 7.4.10 |
| Database | Dedicated `test_geoview_473_6zhkedo2`, migrated from empty |
| Redis | Reserved test databases 14 / 15 |
| Browser | Headless Chromium through Playwright; temporary `127.0.0.1:8473` server |

The existing local NetBox checkout, virtual environment and development database
were not upgraded. Test settings load connection credentials from the existing
local configuration without copying credentials into this repository. The
candidate's tracked files were compared with the checkout: `version.py` is the
only difference. Source imports, app registration, map URL resolution, template
origins and static-file origins were asserted for both plugin copies.

## Results

| Check | Result |
|---|---|
| Development GeoView integration suite | 94 passed, no skips |
| Published 0.8.2 code, existing release-era integration suite | 49 passed, no skips |
| Lightweight utility/theme tests | 6 passed |
| Focused upstream NetBox regressions | 9 passed |
| Existing map browser scenarios | 12 passed |
| Saved-filter/dashboard browser scenarios | 9 passed |
| Device-role filter browser scenarios | 6 passed |
| Device-role color/marker browser scenarios | 5 passed |
| System checks and static collection | Passed; 232 static files collected |
| Migration status | No pending migrations |
| Hierarchy consistency | All 11 core hierarchical models OK |

The integration suite covers authentication, object permissions, selectors,
saved filters, widgets, inclusion/exclusion and descendant roles, role colors,
explicit marker overrides, custom icons, popups, custom fields, coordinates,
Unicode search, hierarchy updates and HTTP proxies. External HTTP is mocked in
integration tests.

All 32 browser checks passed with no uncaught JavaScript errors. They exercise
actual map tiles and Valhalla routing, light/dark popups, desktop/mobile layouts,
native dashboard configuration forms, widget refresh and unavailable filters.
Additional role checks exercise the live dynamic device selector when switching
to exclusion, saved role filters, nested/empty roles, and matching widget data.
Color checks compare all 16 isolated fixture devices with their actual role
colors and configured symbols, retain site marker colors, and render a custom
image and an explicit color override using backend-generated configuration.
Desktop, mobile and dark-popup screenshots were inspected.

The source archive lacks generated documentation assets, producing the existing
`staticfiles.W004` warning for `project-static/docs`. The inherited test
configuration also emits the existing `LOGIN_REQUIRED` deprecation warning.
Neither warning prevented registration or successful checks.

## NetBox changes reviewed

Sources: [official 4.7.3 release notes](https://github.com/netbox-community/netbox/releases/tag/v4.7.3)
and the [4.7.2–4.7.3 comparison](https://github.com/netbox-community/netbox/compare/v4.7.2...v4.7.3).

- Device API field selection and config-context loading changed. GeoView's
  selector inherits `DeviceViewSet`; its integration cases and actual browser
  selector requests pass. Four targeted upstream tests also validate omitted,
  requested and default config context, plus field-dependent prefetching.
- User-preference initialization and missing-preference login handling changed.
  Five upstream regressions pass, as do native dashboard/widget browser checks.
- Filter validation and the Django/django-filter dependencies changed. GeoView's
  real filter forms, tree filters, exclusions and malformed-input tests pass
  without adaptation.
- GraphQL initialization is deferred for management commands, while WSGI loads
  the URL configuration at startup. The temporary server starts successfully
  with the plugin, and all browser suites pass.

The nine upstream tests are:

```text
dcim.tests.test_api.DeviceTestCase.test_config_context_included_by_default_in_list_view
dcim.tests.test_api.DeviceTestCase.test_config_context_not_loaded_when_omitted
dcim.tests.test_api.DeviceTestCase.test_config_context_loaded_when_requested
dcim.tests.test_api.DeviceTestCase.test_field_prefetches_follow_requested_fields
users.tests.test_preferences.UserPreferencesTestCase.test_login_creates_missing_userconfig
users.tests.test_signals.CreateUserConfigSignalTestCase
```

## Reproduction and scope

Use the commands in [TESTING.md](../../TESTING.md) with a pinned 4.7.3 source
archive, separate virtual environment and dedicated database. First assert the
unchanged plugin is skipped. Raise only its maximum NetBox version in a copy,
assert its registration/import origins, and run the integration and browser
suites. Run tests sequentially when sharing the reserved Redis databases.

Local wrappers, configuration, browser setup/cleanup scripts, logs, results and
screenshots are retained under `/home/prohph/geoview-netbox473-6zHKedO2/`.
The published wheel contents were tested from the extracted copy, rather than
installed as a newly built wheel. No release was built or published.

The temporary server was stopped, browser sessions revoked, private credential
files removed, and disposable users and their saved filters/dashboard records
deleted. The isolated database and test environment remain available for review.
The normal development server remains on port 8001.

This validates a fresh isolated installation. An in-place production upgrade,
the full upstream NetBox suite, other Python/database versions, Firefox/WebKit,
SSO and load testing were not part of this check. Versions after 4.7.3 are outside
the tested scope.
