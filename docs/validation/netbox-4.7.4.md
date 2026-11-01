# NetBox 4.7.4 compatibility and GeoView 0.10.0 release check — 2026-11-01

GeoView 0.10.0 supports NetBox 4.5.4 through exactly 4.7.4. The 4.7.4 review
required only raising `NETBOX_MAX_VERSION`; no additional runtime adaptation,
plugin dependency or plugin migration was needed. This release also includes
the previously committed status filters, native slugs, tile revalidation and
smoother initial map presentation.

The baseline checkout at `49d140b`, still identifying itself as 0.9.0 with a
maximum of 4.7.3, was archived into a disposable copy. On 4.7.4, NetBox reported
the expected version warning and GeoView was absent from Django's app registry.
The compatibility limit must therefore be updated to enable the plugin.

## Environment

| Component | Version / setup |
|---|---|
| NetBox | Official `v4.7.4`, commit `9b9844bdbc226bc0bacff6bfdf65a824a4be0eec` |
| Plugin | Built 0.10.0 wheel, installed into a new virtual environment |
| Python / Django / DRF | 3.14.7 / 6.1.2 / 3.18.3 |
| Dependencies | Exact 4.7.4 runtime and testing requirements; `pip check` passed |
| PostgreSQL / Redis | 16.15 / 7.4.10 |
| Database | Dedicated `test_geoview_474_ryitpxg`, migrated from empty |
| Redis | Reserved test databases 14 / 15 |
| Browser | Headless Chromium through Playwright; temporary `127.0.0.1:8474` server |

The normal NetBox checkout, virtual environment, database and development server
were not upgraded. Private connection settings were loaded from the existing
local configuration at runtime, without copying credentials into this repository.
Tests and browser fixtures used only the isolated database.

## Results

| Check | Result |
|---|---|
| GeoView integration suite against installed wheel | 105 passed, no skips |
| Focused upstream NetBox regressions | 31 passed |
| Lightweight utility/theme/release-note tests | 14 passed |
| Map browser scenarios | 12 passed |
| Saved-filter/dashboard browser scenarios | 9 passed |
| Status-filter/native-slug browser scenarios | 5 passed |
| Self-contained cache/initial-presentation browser scenarios | 13 passed |
| Package import, registry, URLs, templates and static origins | Passed from installed wheel |
| System checks and static collection | Passed; 232 static files collected |
| Migration status | No pending migrations |

Integration coverage includes authentication and object constraints, selectors,
roles and statuses, saved filters, widgets, marker styles, popups, Unicode search,
hierarchy changes, HTTP proxies and ETag revalidation. A new version-gated
regression creates tagged sites/devices and a tag with IDs above 2,147,483,647,
then verifies map selection, saved widget data and REST device choices.

The browser suites use the installed wheel with three synthetic sites and
16 devices. They check actual map tiles and live Valhalla routes, light/dark
popups, desktop/mobile layouts, native dashboard configuration, independent
widgets, refresh without replacing tiles, unavailable filters, custom status
choices and slug generation/manual overrides. No uncaught JavaScript errors
were reported. Desktop/mobile status-filter and map/widget screenshots were
reviewed.

The additional self-contained suite serves the checkout's actual JavaScript,
CSS and Leaflet assets with synthetic HTTP responses. It exercises full page
reloads, conditional tile requests, final-viewport initialization, delayed/failed
tiles, the 12-second fallback and HTMX cleanup. These 13 checks do not require
a NetBox server and are counted separately from the 26 installed-wheel checks.

## Upstream changes reviewed

Sources: [official 4.7.4 release notes](https://github.com/netbox-community/netbox/releases/tag/v4.7.4)
and the [4.7.3–4.7.4 comparison](https://github.com/netbox-community/netbox/compare/v4.7.3...v4.7.4).

- Dynamic model fields, APISelect widgets and the HTMX object selector changed.
  Their upstream regressions and GeoView's real forms/selectors passed.
- REST serializers and device config-context handling changed, alongside a DRF
  upgrade. GeoView's inherited device choices and the focused device API/cache
  regressions passed without changes.
- The `TaggedItem.object_id` column is widened by NetBox migration
  `extras.0145_taggeditem_object_id_bigint`. The new GeoView regression verifies
  tagged objects with IDs above the former 32-bit limit after migration.
- GraphQL, Pillow and sorl-thumbnail dependencies changed. The exact pinned
  dependency set passed installation, metadata checks and application startup.

The 31 upstream tests are selected by these labels:

```text
netbox.tests.test_htmx
utilities.tests.test_apiselect
utilities.tests.test_forms.DynamicModelChoiceFieldTestCase
extras.tests.test_configcontext_cache.ConfigContextCacheReadPathTest
dcim.tests.test_api.DeviceTestCase.test_config_context_read_without_copy
dcim.tests.test_api.DeviceTestCase.test_config_context_graphql_selection
dcim.tests.test_api.DeviceTestCase.test_config_context_included_by_default_in_list_view
dcim.tests.test_api.DeviceTestCase.test_config_context_not_loaded_when_omitted
dcim.tests.test_api.DeviceTestCase.test_config_context_loaded_when_requested
dcim.tests.test_api.DeviceTestCase.test_field_prefetches_follow_requested_fields
```

NetBox's upstream upgrade notes also apply independently of GeoView: deployments
using an aliased storage backend with `STORAGES` options may need
`manage.py thumbnail clear`; circuit-status GraphQL queries must use the new
`CircuitStatusEnum` values prefixed with `STATUS_`. GeoView does not depend on
either interface.

## Package validation and scope

All 61 tracked plugin source/resource files were compared byte-for-byte with
the wheel, including translations, templates, Leaflet assets, management
commands and packaged test-data JSON. Metadata identifies version 0.10.0,
Python >=3.12 and no additional runtime dependencies. Package smoke checks
assert imports from the new environment's `site-packages`, registration, URLs
and installed template/static origins before the integration/browser runs.

The source archive omits generated documentation assets, resulting in the
existing `staticfiles.W004` warning for `project-static/docs`. Inherited settings
also emit NetBox's `LOGIN_REQUIRED` deprecation warning. Neither warning prevents
plugin registration, system checks or tests.

Local settings, runners, logs, package artifacts and screenshots are retained
under `/home/prohph/geoview-netbox474-_ryitpxg/`. The temporary browser server was
stopped, its session revoked, private session files removed, and the disposable
user and owned saved filters/dashboard removed. The isolated database and
synthetic fixtures remain available for review.

Use the commands in [TESTING.md](../../TESTING.md) with the official pinned source,
separate virtual environment and dedicated database. Run suites sequentially
when they share the reserved Redis databases. This check validates a fresh
isolated installation; it does not cover an in-place production upgrade, the
complete upstream suite, other Python/database versions, Firefox/WebKit or SSO.
Older supported NetBox patches were not revalidated by this 4.7.4 check.
