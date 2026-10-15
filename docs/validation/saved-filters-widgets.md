# Saved filters and dashboard widgets — 2026-10-15

This validates the unreleased feature in the working checkout based on GeoView
0.8.2. It is not a new published version. NetBox compatibility metadata remains
4.5.4–4.7.2; this report specifically tests 4.5.10, 4.6.10 and 4.7.2.

## Matrix and results

| NetBox | Python | Django | Integration tests | Widget browser checks |
|---|---|---|---|---|
| 4.5.10 | 3.13.14 | 5.2.13 | 68 passed, 1 expected skip | 9 passed |
| 4.6.10 | 3.13.14 | 6.0.8 | 68 passed, 1 expected skip | 9 passed |
| 4.7.2 | 3.14.7 | 6.1.1 | 69 passed | 9 passed |

The skip is the pre-existing Unicode regression for a core fix introduced in
NetBox 4.7.1. All six utility/theme unit tests pass. No uncaught JavaScript errors
were recorded in the dashboard browser runs. Screenshots of light/dark popups
and mobile dashboards were retained and visually inspected.

The existing full-map browser suite also passed all 12 checks on 4.7.2, including
filters, custom fields, light/dark popups, desktop/mobile layouts, direct distance,
and real Valhalla car/bicycle/pedestrian routes. The Vienna–Linz car route returned
207.265 km / 141.5 minutes and 2,933 geometry points; direct distance was 155 km.
Live route data may change independently of the plugin.

## Scope

The 20 additional integration tests exercise:

- Creating a NetBox SavedFilter from the GeoView form, updating the same record,
  copying it and reloading it by reference.
- Flattening nested accessible references, omitting map settings and inactive
  operators, explicit overrides and clearing an edited condition.
- Saved exclusions, conflicting operators, incompatible/unsupported conditions,
  circular references, missing/disabled filters and empty results.
- Restricting device results with site conditions and keeping the widget's marker
  data equal to the full map for the same filter.
- CSRF and add/change permissions, filter ownership, sharing changes and
  constrained object permissions. Shared filters do not grant object access.
- Native widget registration and NetBox's actual dashboard add/configuration
  serialization, with integer filter IDs and independent widget settings.
- Request-scoped widget form choices: a forged or revoked private selection
  cannot reveal its name in the configuration dialog or be submitted successfully.

The nine browser scenarios create a filter through the GeoView UI, preserve an
exclusion operator, add two native widgets with different filters and marker
sets, open popups, refresh, simulate a missing filter reference, remove old
marker data, reinitialize through HTMX, resize, check popup bounds and themes,
and verify mobile horizontal overflow, visible refresh controls and marker bounds
after resizing. Leaflet and the shared renderer load once.
Popup size follows the widget and its top controls yield space while the popup
is open; bottom attribution stays visible.

The selector/add forms and response data are real NetBox views, not mocked
widget classes. Integration tests mock external HTTP; browser maps use the
configured tile service. No new database models or migrations were introduced.

## Environments and reproduction

Official 4.5.10 and 4.6.10 tags were extracted with `git archive` from the local
NetBox repository into `/home/prohph/geoview-widget-matrix-OhBe5D/`. Separate
virtual environments installed each tag's complete `requirements.txt`.
The existing isolated 4.7.2 environment at
`/home/prohph/geoview-netbox472-3l4t293z/` was reused with the current plugin
checkout first on `PYTHONPATH`.

Databases were `test_geoview_widgets_4510`, `test_geoview_widgets_4610`, and
`test_netbox_geoview_472_3l4t293z`. The configuration reads local connection settings
at runtime; credentials are not copied into this repository. Redis databases
14/15 are the reserved test databases. The final matrix integration run was
sequential. Existing NetBox source, its virtual environment and development data
were not upgraded or migrated.

Temporary browser listeners used ports 18510, 18610 and 18720. Each test database
was seeded with the existing GeoView fixture command. Browser authentication
used a test-only account with an unusable password and temporary session.
The account's dashboard was disposable; no ordinary user's dashboard was changed.

Use [TESTING.md](../../TESTING.md) for the integration and browser commands, with
each isolated NetBox path/configuration. The retained matrix directory contains
`matrix_configuration.py`, the setup script and browser results in
`browser4510`, `browser4610`, `browser472` and `fullmap472`. Browser credentials
are temporary and must not be reused or committed.

Source archives report `staticfiles.W004` because generated documentation static
files are absent. NetBox 4.6/4.7 also reports its existing LOGIN_REQUIRED
deprecation warning. Neither warning prevented registration or the tests.

## Package checks

The development wheel and source distribution passed `twine check`. The wheel
was installed into a separate target directory and loaded ahead of the source
checkout on NetBox 4.7.2. Smoke checks assert installed-package imports, widget
registration, data URL resolution, both new templates and the widget/map static
assets. Static collection and migration checks passed, followed by all 69
integration tests against the installed wheel. Dependency checks passed for all
three virtual environments. The base package version is retained for local
validation; publishing the feature requires a new release version.

## Limits

This is local feature validation against PostgreSQL/Redis and Chromium, not the
full NetBox upstream suite, a production upgrade/restore, a load test or an SSO
validation. Other older patches and NetBox 4.7.3 have not been validated by this
feature check. The widget initially supports one saved filter, manual refresh and
the existing GeoView filter subset; it does not provide arbitrary NetBox/custom
field filtering or embedded routing.
