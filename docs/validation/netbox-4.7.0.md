# Local NetBox 4.7.0 validation — 2026-09-06

This report records the local plugin integration and browser validation for
GeoView 0.8.0 on NetBox 4.7.0. The previous 0.7.0 package declares a maximum of
NetBox 4.6.99.

## Environment and isolation

| Component | Version / setup |
|---|---|
| NetBox | 4.7.0, local `/home/prohph/netbox` checkout |
| Django | 6.1 |
| Python | 3.14.7 in `netbox-dev` |
| PostgreSQL | 16.15 |
| Redis | 7.4.10 |
| Browser | Chromium 151.0.7922.34, Playwright |
| Plugin | Source changes for 0.8.0, based on 0.7.0 |
| Integration database | `test_netbox_geoview`, created and migrated separately |
| Integration Redis | Databases 14 and 15 |
| Browser server | Additional local listener on `127.0.0.1:8001` |

GeoView was installed editable in the new NetBox virtual environment. A temporary
configuration enabled only GeoView for testing. The user's `configuration.py`
and normal server on port 8000 were left unchanged during that validation.
Integration fixtures were seeded only in the test database. Browser tests used
the existing local development sites/devices and a temporary authenticated session.

After validation, GeoView was enabled in the local `configuration.py` at the
user's request, static assets were collected, and the normal server was restarted.
The local configuration contains instance settings and is not part of this repository.
All 12 browser scenarios also passed on the activated server at port 8000.

## Results

| Check | Result |
|---|---|
| Existing utility/theme unit suite | 6 passed |
| PostgreSQL integration suite | 39 passed |
| Dynamic dropdown API endpoints | 12 endpoints checked within the integration suite |
| Browser scenarios | 12 passed |
| Python coverage with branch measurement | 87% combined coverage; not exhaustive coverage |
| `manage.py check`, plugin registry and URLs | Passed with GeoView actually loaded |
| Local database migration status (`migrate --check`) | Passed; no pending migrations |
| Dependency consistency (`pip check`) | Passed |
| Wheel and sdist build, `twine check` | Passed |
| Isolated wheel import, templates/fixture resources and `collectstatic` | Passed; assets collected into a temporary directory |

Integration coverage includes map/filter/apply pages, each main filter family,
include/exclude operators, tags and untagged devices, saved-filter IDs/slugs,
own/site-fallback/zero/missing coordinates, popup configuration and escaped
custom-field data, repeated seeding, nested locations and transaction rollback.
It also covers authentication, object restrictions, private/disabled saved
filters, routing profiles/alternatives and error handling, and tile-proxy caching,
unknown layers, timeouts and non-image responses.

The real browser exercised form submission, light/dark device popups, map tile
loading, route selection, direct distance, live routing, panel collapse/clear,
and 1920×1080, 1366×768 and 390×844 viewports. No uncaught JavaScript errors were
recorded. Desktop pages fit vertically; mobile pages have no horizontal overflow.
Normal vertical scrolling remains possible on mobile for NetBox's footer and
the full route panel.

Live Valhalla results at test time:

| Profile / route | Distance | Duration |
|---|---|---|
| Car, Vienna DC → Linz Hub | 204.005 km | 141.4 min |
| Direct distance, Vienna DC → Linz Hub | 155 km | — |
| Bicycle, short Vienna fixture route | 1.570 km | 5.6 min |
| Pedestrian, same short Vienna fixture route | 0.232 km | 2.7 min |

Route lengths can differ by profile and can change with upstream map data.
The live tests used the configured public Valhalla service, not a local routing
daemon. Error-path tests mock the upstream service so they are repeatable.

## Findings and changes

1. **Plugin loading:** the new virtual environment initially lacked GeoView,
   and the plugin's 4.6.99 maximum prevented activation. NetBox can emit a warning
   and still return success from `check` after skipping a plugin. Tests now verify
   the app registry, URLs and templates explicitly. The source maximum is 4.7.0.
2. **Permissions:** the original plain Django views did not enforce NetBox's
   login requirement or restrict map/filter querysets. The views now use NetBox's
   conditional login mixin and restricted querysets. Saved filters must be
   enabled, permitted and shared or owned by the current user.
3. **Invalid input:** malformed saved-filter IDs previously raised `ValueError`
   before form validation. They now produce normal form errors. `NaN` and other
   non-finite coordinates are rejected with HTTP 400 before contacting Valhalla.
4. **Narrow layouts:** a long site-filter badge widened the document from 390 to
   471 pixels. Badges now wrap. The unused mobile grid row was removed when the
   route panel is hidden, allowing the map to use the available height.

The permission, invalid-input and layout issues were found during this
validation; they have not been established as regressions introduced by NetBox
4.7.0. No change to NetBox itself or to the fixture schema was needed.

## NetBox 4.7 changes reviewed

The [official 4.7.0 release notes](https://github.com/netbox-community/netbox/releases/tag/v4.7.0)
and local NetBox source were checked against the plugin:

- The move from MPTT to PostgreSQL `ltree` did not break GeoView's name-ordered
  filter querysets or parent-based fixture creation. Nested-location creation,
  ancestors and repeated seeding passed against the new schema.
- Changes to `CustomField.objects.get_for_model()` do not require adapting
  GeoView's popup mapping: it reads `custom_field_data` directly. Custom-field
  creation and the packaged fixture data were exercised in the test database.
- The removal of NetBox's old `querystring` template tag does not affect these
  templates; they do not use it. All GeoView page templates rendered successfully.
- GeoView does not use the removed django-tables2 column, mail backend settings,
  legacy view action constants or removed registry entries mentioned in the notes.

## Scope and follow-up

This is a plugin validation on the specified local runtime, not a run of the
entire upstream NetBox test suite, a load test or a complete security audit.
Older NetBox/Python combinations, Firefox/WebKit, SSO, production reverse proxies,
every optional tile provider and every configuration combination were not
re-tested. No production support claim is made for later 4.7.x releases.

The repeatable commands are in [TESTING.md](../../TESTING.md). Local browser
screenshots, `results.json`, coverage data and package artifacts were stored in
`/tmp/geoview-netbox47-qXANRa/`; temporary artifacts are not part of the release
and may be removed by the operating system.

GeoView 0.8.0 packages these validated changes. Before extending support to
additional NetBox versions, recheck the versions that will remain in the declared
compatibility range and follow [RELEASING.md](../../RELEASING.md).
