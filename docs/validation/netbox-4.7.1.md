# Local NetBox 4.7.1 validation — 2026-09-17

The development checkout is compatible with NetBox 4.7.1 in the environment
below after increasing `NETBOX_MAX_VERSION` from `4.7.0` to exactly `4.7.1`.
No functional plugin changes or plugin database migrations were necessary.
This is an **unreleased** compatibility change: the published GeoView 0.8.0
package still declares a maximum of NetBox 4.7.0.

## Environment and isolation

| Component | Version / setup |
|---|---|
| NetBox | Official `v4.7.1` tag, commit `abccf4e03`, separate detached worktree |
| Django | 6.1.1 |
| Python | 3.14.7 in `netbox-dev`, separate virtual environment |
| Dependencies | Installed from the 4.7.1 `requirements.txt`; `pip check` passed |
| PostgreSQL / Redis | 16.15 / 7.4.10 |
| Browser | Chromium 151.0.7922.34 through Playwright |
| Plugin | GeoView 0.8.0 source plus the unreleased compatibility/test/docs changes |
| Test database | `test_netbox_geoview_471`, migrated separately |
| Test Redis databases | 14 / 15 |
| Browser server | Temporary listener on `127.0.0.1:8471` |

The existing `/home/prohph/netbox` checkout, virtual environment,
`configuration.py`, and development database were not upgraded or migrated.
The disposable configuration reads existing connection and routing settings
without copying credentials into this repository. Integration and browser
fixtures were seeded only in the isolated test database. Browser authentication
used a temporary session for a test-only account with no usable password.

## Results

| Check | Result |
|---|---|
| Utility/theme unit tests | 6 passed |
| GeoView PostgreSQL integration tests | 43 passed (39 existing + 4 new) |
| Focused upstream NetBox regression tests | 34 passed |
| Browser scenarios | 12 passed |
| Combined Python coverage, including branches | 87%; not exhaustive coverage |
| Plugin registry, URL resolution, system checks | Passed with GeoView loaded |
| Test database migration status | No pending migrations |
| `rebuild_ltree_paths --check` on seeded test database | All 11 core hierarchical models OK |
| Static collection | Passed in the disposable NetBox worktree |
| Wheel/sdist build and `twine check` | Passed |
| Isolated wheel import, templates, resources and static collection | Passed |
| GeoView integration suite against the installed wheel | 43 passed |

The first startup with the published 0.8.0 version limit emitted a warning and
skipped GeoView even though `manage.py check` returned success. After the version
limit change, the app registry, plugin URLs, rendered views and browser checks
confirmed that GeoView was actually enabled.

The local build retains the source version number 0.8.0 for validation only;
it is not the published PyPI artifact and was not uploaded. Select a new version
before releasing these changes. The wheel was installed into a separate target
directory, and its import/template paths were asserted before testing.

The four added integration tests cover:

- Device search for `straße` and `STRASSE` in both the GeoView map and NetBox's
  dynamic device selector. This regression is skipped below NetBox 4.7.1 because
  the core collation fix was introduced there.
- Region/site-group moves and renames, descendant paths, map selection and
  cascading site-selector API results.
- Nested location moves and renames without losing a device's coordinates or
  map marker.
- Multiselect custom-field values rendered in a device popup.

Browser checks cover map assets/tiles, filter submission, light/dark popup
colors and custom fields, direct distance, live routing, route-panel controls,
and 1920×1080, 1366×768 and 390×844 viewports. No uncaught JavaScript errors were
recorded. Desktop content fits the viewport; mobile has no horizontal overflow
and retains normal vertical scrolling. Dark popup and mobile screenshots were
also reviewed visually.

| Live route | Distance | Duration |
|---|---|---|
| Car: Vienna DC → Linz Hub | 204.005 km | 141.4 min |
| Direct distance: Vienna DC → Linz Hub | 155 km | — |
| Bicycle: short Vienna route | 1.570 km | 5.6 min |
| Pedestrian: same short Vienna route | 0.232 km | 2.7 min |

Live tests used the configured public Valhalla service. These results may change
with upstream map data; integration tests mock external HTTP for repeatability.

## Relevant NetBox 4.7.1 changes

Source: [official release notes](https://github.com/netbox-community/netbox/releases/tag/v4.7.1).

- **Hierarchy triggers (#23130):** the corrected core migrations apply cleanly
  in the test database. The focused upstream tests check restore-safe trigger
  creation, installed definitions, corrective operations for missing/old
  triggers, and detection/repair of stale paths. GeoView registers no models of
  its own and therefore needs no `ReinstallLtreeTriggers` plugin migration.
- **Case-insensitive collation (#23012):** both GeoView's ORM search and the
  NetBox selector API benefit from the core fix; no plugin workaround is needed.
- **Negated multiselect custom-field filters (#23117):** the upstream regression
  passes. GeoView reads custom fields for popup display, which also passes.
  Arbitrary `cf_*` filters are not implemented by GeoView's map filter form,
  including when supplied by saved filters; this is a pre-existing limitation,
  not newly added filtering support.
- **SSO/CSP (#23112):** the change is in NetBox's login flow. Authenticated and
  anonymous GeoView behavior passed, but external SSO was not tested.
- The pinned Django, django-rq, Redis client and Strawberry updates required no
  changes to GeoView's imports, templates, views or proxies.

### Upgrade warning: databases restored from NetBox 4.7.0

A 4.7.0 dump restore could omit cascade triggers. Upgrading reinstalls them but
does **not** repair previously stale `path` or `sort_path` values. After upgrading
an affected instance, run this read-only check from its NetBox repository root:

```bash
python netbox/manage.py rebuild_ltree_paths --check
```

If it reports damage, follow the
[official repair guide](https://github.com/netbox-community/netbox/blob/v4.7.1/docs/administration/repairing-hierarchical-paths.md).
Back up first and schedule repairs in a maintenance window: rebuilding rewrites
and locks the affected table rows. No such repair was run on the existing local
development database during this validation.

## Reproduction and scope

Run the plugin suites as described in [TESTING.md](../../TESTING.md), using a
separate database, configuration and environment for the NetBox version under
test. The focused upstream run used these labels with `manage.py test`:

```text
dcim.tests.test_filtersets.DeviceCollatedFilterTestCase
extras.tests.test_customfields.CustomFieldModelFilterTestCase.test_filter_multiselect
utilities.tests.test_ltree.RestoreUnderRestrictedSearchPathTests
utilities.tests.test_ltree.CascadeTriggerDefinitionTests
utilities.tests.test_ltree.CorrectiveMigrationTests
utilities.tests.test_management_commands.RebuildLtreePathsTestCase
```

This was a fresh isolated 4.7.1 test database, not an in-place upgrade or full
restore of the user's development database. The focused trigger tests simulate
the relevant old/missing-trigger states; they are not a complete backup/restore
rehearsal. The full upstream NetBox suite, older NetBox/Python combinations,
Firefox/WebKit, production proxies, load tests and external SSO were not run.
No compatibility claim is made for later 4.7.x versions.

Local logs, screenshots, coverage data and disposable environment are under
`/tmp/geoview-netbox471-4A2xVL/` and may be removed by the operating system.
The temporary server was stopped and its browser session revoked; the credential
file was removed. The isolated test database was retained for repeat runs.
The temporary files are not release assets. No tag or PyPI publication is part
of this validation; follow [RELEASING.md](../../RELEASING.md) for the next release.
