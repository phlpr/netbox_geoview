# NetBox 4.7.2 compatibility check — 2026-10-01

GeoView 0.8.1 passed the checks below on NetBox 4.7.2 after changing only
`NETBOX_MAX_VERSION` from `4.7.1` to `4.7.2` in a disposable source copy.
No functional plugin changes or plugin database migrations were needed.

**The unchanged GeoView 0.8.1 release does not load on NetBox 4.7.2.**
NetBox warns that the maximum supported version is 4.7.1 and skips the plugin,
even though `manage.py check` exits successfully. This was reproduced and the
absence of GeoView from Django's app registry was asserted before testing the
adjusted copy. The expanded version limit is included in GeoView 0.8.2.

## Environment

| Component | Version / setup |
|---|---|
| NetBox | Official `v4.7.2` tag, commit `251458b89a5eb2f5fe0d20ecd1140ba08f141a9c` |
| Plugin | GeoView 0.8.1 at `ea233c1`, copied with `git archive`; only its maximum NetBox version changed |
| Python / Django | 3.14.7 / 6.1.1 |
| Dependencies | Separate virtual environment using the 4.7.2 `requirements.txt`; `pip check` passed |
| PostgreSQL / Redis | 16.15 / 7.4.10 |
| Browser | Playwright 1.62.1 with Chromium 151.0.7922.34 |
| Database | Dedicated `test_netbox_geoview_472_3l4t293z`, migrated from empty |
| Redis | Reserved test databases 14 / 15 |
| Browser server | Temporary `127.0.0.1:8472` listener |

The existing NetBox checkout, virtual environment and development database were
not upgraded or migrated. The test configuration reads existing connection and
GeoView settings without storing credentials in this repository. Browser data
was seeded only in the dedicated database; authentication used a temporary
session for a test-only account with an unusable password.

## Results

| Check | Result |
|---|---|
| Utility/theme unit tests | 6 passed |
| GeoView integration tests | 49 passed, no skips |
| Focused upstream NetBox regressions | 14 passed |
| Existing browser scenarios | 12 passed |
| Additional invalid GET filter browser regression | Passed |
| Plugin registry, source import and map URL resolution | Passed with the adjusted copy loaded |
| System checks | Passed with the source-archive documentation warning below |
| Static collection | 231 files collected successfully |
| Migration status | No pending migrations |
| Hierarchy consistency | All 11 core hierarchical models OK |

The integration suite covers actual menu/template rendering, all five GeoView
endpoints, authentication and object permissions, permission revocation after
tile caching, dynamic selectors, saved filters, Unicode search, hierarchy moves,
coordinates, popups, custom fields, seed rollback, and routing/tile proxies.
External HTTP is mocked in these integration tests.

Browser scenarios use actual tiles and the configured Valhalla service. They
cover filter submission, light/dark popups, direct distance, route controls,
car/bicycle/pedestrian routing, and 1920×1080, 1366×768 and 390×844 layouts.
No uncaught JavaScript errors were recorded. Dark popup and mobile screenshots
were also inspected. The extra browser check confirms that an invalid GET
filter still renders, does not steal focus, and leaves the filter tab usable.

The Vienna–Linz car route returned 204.006 km / 141.4 minutes; direct distance
was 155 km. Short Vienna bicycle/pedestrian routes returned 1.570 km / 5.6 minutes
and 0.229 km / 2.7 minutes. Live results can change with upstream routing data.

The source archive lacks generated documentation assets, so system checks emit
`staticfiles.W004` for `project-static/docs`. The test configuration also emits
NetBox's deprecation warning for `LOGIN_REQUIRED`; neither warning prevents the
plugin from loading or the tests from passing.

## NetBox changes reviewed

Sources: [official 4.7.2 release notes](https://github.com/netbox-community/netbox/releases/tag/v4.7.2)
and the [4.7.1–4.7.2 source comparison](https://github.com/netbox-community/netbox/compare/v4.7.1...v4.7.2).

- **Form error focus (#22949):** NetBox changes global JavaScript, HTMX handling
  and tabbed field rendering. The five upstream tabbed-field tests pass, as do
  GeoView's browser filter scenarios and the additional invalid GET filter check.
- **Owner related objects (#23203):** six relation-discovery tests and three
  owner-view tests pass, including constrained permissions. GeoView's own
  tenant/owner filtering and permission tests also pass.
- **REST API sync permissions and background token creation (#23197, #23196):**
  these changes concern sync/write actions which GeoView does not implement.
  The plugin's actual selector APIs and endpoint access controls pass their tests.
- Dependency updates required no changes to GeoView's imports, forms, templates,
  views or HTTP proxies in this environment.

NetBox's release notes also identify a core issue in 4.7.0/4.7.1: API tokens
created through background bulk requests could appear in job results. They
advise replacing tokens created through that path. This check did not inspect
the existing development database or its tokens.

## Reproduction and scope

Use the suites in [TESTING.md](../../TESTING.md) with an isolated NetBox 4.7.2
source archive, virtual environment and database. First check the unchanged
plugin and assert it is absent from the app registry. Then change only the
maximum version to 4.7.2 in the test copy and verify its import path, registration
and URLs before running the integration and browser suites.

The focused upstream run used these labels with `manage.py test --keepdb --noinput`:

```text
utilities.tests.test_templatetags.RenderFieldsetTabsTestCase
utilities.tests.test_relations.GetRelatedModelsTestCase
users.tests.test_views.OwnerTestCase.test_related_objects_list_owned_objects
users.tests.test_views.OwnerTestCase.test_related_objects_honor_object_permissions
users.tests.test_views.OwnerTestCase.test_related_objects_honor_constrained_permissions
```

This validates a fresh isolated installation, not an in-place production upgrade
or backup/restore. The full upstream suite, other Python and database versions,
Firefox/WebKit, external SSO, production proxies and load tests were not run.
No compatibility claim is made for versions after 4.7.2.

Local scripts, logs, screenshots and the disposable environment are under
`/home/prohph/geoview-netbox472-3l4t293z/`. The temporary server was stopped,
the browser session revoked, its credential file removed and the test account
disabled. The isolated database and test environment are retained for inspection.
The initial check used only the disposable copy; GeoView 0.8.2 incorporates the
validated compatibility-limit change.

## GeoView 0.8.2 release package validation

Both the wheel and source distribution were built and passed `twine check`.
All 54 plugin source/resource files in the wheel were compared with the release
checkout, including templates, JavaScript/CSS, Leaflet assets, translations,
the seed command and fixture JSON. The source distribution contains the release
documentation, this report and the integration/browser tests.

The wheel was installed without dependencies into the isolated NetBox 4.7.2
environment, which had not previously installed GeoView as a package. The
release runner excludes the source copy from `PYTHONPATH`. Smoke checks assert
that GeoView imports from the virtual environment's `site-packages`, its
metadata and app version are 0.8.2, its NetBox limits are 4.5.4–4.7.2, and its
templates/static assets resolve from the installed package.

All 49 integration tests passed again against the installed wheel, with no
skips. System checks and static collection passed with the same documentation
warning described above. The six lightweight tests also passed. The earlier
browser results apply to the same functional code and assets; the release
changes only the plugin version and supported NetBox maximum.
