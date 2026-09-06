# Testing GeoView locally

The lightweight suite needs only Python. The integration suite runs inside a
real NetBox environment against PostgreSQL and Redis. Browser tests use a local
NetBox server with GeoView enabled and exercise its actual JavaScript and CSS.

## Unit tests

From the plugin repository:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

## Integration tests

Install this checkout in the virtual environment of the NetBox version under test:

```bash
/home/prohph/netbox/venv/bin/pip install --no-deps -e /home/prohph/netbox_geoview
```

Run in `netbox-dev` on the local development machine:

```bash
toolbox run -c netbox-dev env \
  PYTHONPATH=/home/prohph/netbox_geoview/tests \
  NETBOX_CONFIGURATION=netbox_configuration \
  /home/prohph/netbox/venv/bin/python /home/prohph/netbox/netbox/manage.py test \
  /home/prohph/netbox_geoview/tests/integration --keepdb --noinput
```

Adjust paths for other machines; omit the `toolbox run -c netbox-dev` prefix
when already inside the container. `tests/netbox_configuration.py` imports local
connection credentials from `netbox.configuration`, enables only GeoView and
disables the debug toolbar. It uses the dedicated database `test_netbox_geoview`
and Redis databases 14/15. Reserve those names/databases for these tests before
running them. The PostgreSQL role must be allowed to create test databases.
No credentials are stored in this repository.

The suite seeds its own fixtures in the test database. Tests roll back their
changes. `--keepdb` preserves only the test schema between runs, saving the cost
of applying all NetBox migrations again. The normal development database is not
seeded, flushed or migrated by this command.

Tests cover actual template rendering, filters and permissions, coordinates,
popups, custom fields, saved filters, fixture idempotency and transaction rollback,
plus routing and tile-proxy success/error handling. These integration tests mock
external HTTP calls; the browser suite separately checks the configured live
tile and Valhalla services.

## Browser tests

Use Playwright with its Chromium browser installed. Start an additional local
NetBox server with GeoView enabled (for example on `127.0.0.1:8001`) and the
GeoView fixture sites/devices available. The suite also expects a working
Valhalla configuration. It does not change the account password or theme
preference stored on the server; theme changes use the browser's local storage.

Supply a private JSON file containing a valid cookie for a local test session:
`{"name":"sessionid","value":"...","domain":"127.0.0.1","path":"/"}`.
Treat that file as a credential, restrict its permissions, and revoke the test
session after use. Do not commit it. Set the IDs of the three seeded sites:

```bash
GEOVIEW_BASE_URL=http://127.0.0.1:8001 \
GEOVIEW_COOKIE_FILE=/private/path/session.json \
GEOVIEW_SITE_IDS=1,2,3 \
GEOVIEW_ARTIFACTS=/tmp/geoview-browser-results \
node tests/browser/geoview.cjs
```

`playwright` must be resolvable by Node (or supplied through `NODE_PATH`). The
browser script writes screenshots and `results.json` into the artifact directory
and exits nonzero on failures. It checks filter submission, light/dark popups,
direct distance, a live Wien–Linz route, route-panel controls, desktop/mobile
layout and uncaught JavaScript errors. Additional matching devices in a local
development database are allowed.

## Package validation

Follow [RELEASING.md](RELEASING.md) for wheel/sdist builds, metadata validation,
clean installation, `manage.py check` and `collectstatic` checks.

Always confirm that GeoView is actually installed in Django's app registry:
NetBox can report a successful system check while skipping an incompatible
plugin with a warning. Tests must verify the plugin's URLs and rendered views.

See [the NetBox 4.7.0 report](docs/validation/netbox-4.7.0.md) for the recorded
local validation and limitations. GitHub CI currently runs the lightweight
suite; it does not run this local integration/browser environment automatically.
