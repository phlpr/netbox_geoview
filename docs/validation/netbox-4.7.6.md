# NetBox 4.7.6 compatibility and GeoView 0.10.2 — 2026-11-26

GeoView 0.10.2 supports NetBox 4.5.4 through exactly 4.7.6. Only the package
version and maximum NetBox version change in runtime code. No functional
adaptation, additional plugin dependency or plugin migration is required.
Older supported NetBox patches were not revalidated by this compatibility-only
release. Unchanged GeoView 0.10.1 is correctly excluded on 4.7.6 by its maximum
version guard; a successful NetBox system check alone does not verify that the
plugin was loaded.

## Environment

| Component | Version / setup |
|---|---|
| NetBox | Official `v4.7.6`, commit `4cfaa8f7b45fc2e8bf95309909880c70e80bef64` |
| GeoView | Built 0.10.2 wheel installed in a new virtual environment |
| Python / Django / DRF | 3.14.7 / 6.1.3 / 3.18.3 |
| django-taggit / psycopg / Gunicorn | 7.0.0 / 3.3.9 / 27.0.1 |
| Dependencies | Official pinned runtime/testing requirements; dependency check passed |
| PostgreSQL / Redis | 16.15 / 7.4.10 |
| Integration/browser database | Dedicated `test_geoview_476_88oow9dx`, migrated from empty |
| Upgrade database | `test_geoview_476_upgrade_88oow9dx`, copied from isolated 4.7.5 fixtures |
| Redis | Reserved test databases 14 / 15; database test suites run sequentially |
| Browser | Chromium through Playwright, temporary `127.0.0.1:8476` listener |

Private connection settings were loaded at runtime. No credentials were copied
into this repository. The regular NetBox source, virtual environment and
development database were not upgraded, migrated or seeded.

## Results

| Check | Result |
|---|---|
| GeoView installed-wheel integration suite | 111 passed, no skips |
| Focused upstream NetBox regressions | 98 passed |
| Lightweight utility/theme/release-note tests | 14 passed |
| Full-map browser scenarios | 12 passed |
| Saved-filter/dashboard browser scenarios | 9 passed |
| Device-role filter browser scenarios | 6 passed |
| Device-role color/marker browser scenarios | 5 passed |
| Device-status/native-slug browser scenarios | 5 passed |
| Self-contained cache/initial-presentation browser scenarios | 13 passed |
| Installed imports, app/widget registration, URLs, templates and static origins | Passed |
| System/static collection/dependency checks | Passed; 232 static files collected |
| Fresh schema and isolated 4.7.5 upgrade comparison | Passed; no pending migrations |

The four new GeoView integration regressions cover invalid dynamic device
selections and maintenance mode. Invalid IDs render validation errors, leave
the map empty, return HTTP 400 from widget data and can be corrected. The
maintenance tests use `TransactionTestCase` and actual PostgreSQL read-only
sessions: wrapping the requests in `TestCase` transactions would bypass this
enforcement. They verify readable maps, choices, saved-filter forms and existing
dashboard widgets; refused filter creation/update and widget creation without
persisted changes; successful writes after disabling maintenance; and a default
dashboard that remains unsaved. These four tests skip NetBox versions below
4.7.6, where the corresponding upstream fixes are unavailable.

The 37 installed-wheel browser checks exercise native selectors and dashboard
configuration, saved filters, inclusion/exclusion, statuses, nested roles,
independent widgets, themed popups, custom marker colors/symbols/images,
desktop/mobile layouts, tile refresh and real routing. No uncaught JavaScript
errors were reported. Popup, widget and mobile screenshots were visually
inspected. The Vienna–Linz car route returned 207.272 km, 141.3 minutes and
2,957 geometry points; bicycle and pedestrian requests also passed. External
map/routing services may change independently. The 13 self-contained cache
checks use synthetic responses and are counted separately.

## Upstream changes and upgrade notes

Sources: [official release notes](https://github.com/netbox-community/netbox/releases/tag/v4.7.6)
and [4.7.5–4.7.6 comparison](https://github.com/netbox-community/netbox/compare/v4.7.5...v4.7.6).

- NetBox now enforces `MAINTENANCE_MODE` on database sessions and restores
  write access after each request (#23552). GeoView's custom filter views work
  with that middleware without a separate write guard. Writes are unavailable
  during maintenance; the database is unchanged and the native message is
  displayed. Default dashboards and incidental preferences are not saved.
- Dynamic fields handle invalid initial selections. The native HTMX refresh
  also preserves cleared multiple selections (#23603). Existing GeoView
  selection-clearing and browser save/refresh workflows continue to pass.
- Custom colors remain selected in native forms (#23608). Color-widget/form
  regressions and GeoView's configured marker styles pass.
- Null text lookups and negated object-type filters are corrected (#23632,
  #23691). Targeted upstream cases pass; GeoView's object-type selector,
  exclusions and fail-closed saved-filter behavior need no adaptation.
- Plugin event types are available in event-rule forms (#23652). Four upstream
  registration/form cases pass; GeoView itself registers no new event type.
- Protected-object messages and deletion redirects have tightened checks
  (#23398, #23583). The selected permission/redirect regressions pass.
- `netbox upgrade` now rebuilds the config-context cache (#23696). Its sequence
  and skip/read-only behavior pass upstream command tests. The device
  interface-existence filter regression (#23721) also passes.

The 98 upstream tests include the previous selector, HTMX, configuration-context,
SSO stand-in, ordering and shared-name/slug baseline plus focused 4.7.6 checks.
NetBox's own dummy plugins are enabled only for this upstream suite because
one selected test module imports their models. Exact labels are retained in
the validation directory's `upstream-labels.txt`.

The copied 4.7.5 fixture database has no pending 4.7.6 migrations. Applying
`migrate` succeeds, and full-row hashes/counts of nine relevant tables remain
identical: three sites, 16 devices, six locations, eight device types, one
region, one site group, four custom fields, zero saved filters and one tag.
This is a synthetic fixture copy, not a production upgrade test.

The upstream cable-tracing fixes do not update already recorded split paths
(#21960, #23490). For affected installations, follow the official release note
to retrace paths with `manage.py trace_paths --force` after upgrading. No normal
development cable paths were modified by this validation.

## Package checks, cleanup and limits

The final wheel and source archive pass metadata validation. All tracked runtime
resources are compared byte-for-byte with the wheel, including translations,
templates, static/vendor assets, management commands and fixture JSON. The
source archive includes the new regressions and this report. Metadata still
requires Python >=3.12 and adds no runtime dependency. The final installed wheel
is tested again after preparing the documentation and release notes; its runtime
resources match those used for the browser checks.

Source, private configuration loaders, runners, logs, database snapshots and
screenshots remain under `/home/prohph/geoview-netbox476-88oow9dx/`. Browser
accounts have unusable passwords and temporary sessions. Their sessions,
owned saved filters/dashboards and private cookie files are removed after each
suite. The temporary listener is stopped and browser fixtures are cleared from
the integration database before its final test run. The separate upgrade
fixture database is retained for review.

The source archive reports the existing `staticfiles.W004` warning for missing
generated documentation assets. The inherited `LOGIN_REQUIRED` setting emits
NetBox's deprecation warning. Neither affects plugin registration or tests.

This is a local compatibility and release-package check, not the complete
upstream suite, a production restore, a load test, real-provider SSO validation
or a Firefox/WebKit matrix. See [TESTING.md](../../TESTING.md) for reproduction
instructions. Future NetBox versions require explicit validation.
