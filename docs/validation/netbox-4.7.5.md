# NetBox 4.7.5 compatibility and GeoView 0.10.1 — 2026-11-10

GeoView 0.10.1 supports NetBox 4.5.4 through exactly 4.7.5. The only runtime
source change from 0.10.0 is the package version and `NETBOX_MAX_VERSION` in
`version.py`. No functional adaptation, additional plugin dependency or plugin
migration is required. Older supported NetBox patches were not revalidated by
this compatibility-only release.

Unchanged GeoView 0.10.0 was first installed against 4.7.5: NetBox emitted the
expected maximum-version warning and did not register the plugin. A successful
system check alone is therefore insufficient evidence of compatibility. The
candidate wheel's imports, app/widget registration, URLs, templates and static
origins were explicitly checked before its integration and browser tests.

## Environment

| Component | Version / setup |
|---|---|
| NetBox | Official `v4.7.5`, commit `f5bbfca66cc275730150dfb4ca1b158193e25296` |
| Plugin | Built 0.10.1 wheel installed into a new virtual environment |
| Python / Django / DRF | 3.14.7 / 6.1.3 / 3.18.3 |
| django-taggit / psycopg | 7.0.0 / 3.3.8 |
| Dependencies | Official pinned runtime/testing requirements; `pip check` passed |
| PostgreSQL / Redis | 16.15 / 7.4.10 |
| Integration/browser database | Dedicated `test_geoview_475_vqslqhlv`, migrated from empty |
| Upgrade database | `test_geoview_475_upgrade_vqslqhlv`, copied from isolated 4.7.4 fixtures |
| Redis | Reserved test databases 14 / 15; database test suites run sequentially |
| Browser | Chromium through Playwright, temporary `127.0.0.1:8475` listener |

The regular NetBox source checkout, virtual environment and development database
were not upgraded, migrated or seeded. Private connection settings were loaded
at runtime without copying credentials into this repository.

## Results

| Check | Result |
|---|---|
| GeoView installed-wheel integration suite | 107 passed, no skips |
| Focused upstream NetBox regressions | 48 passed |
| Lightweight utility/theme/release-note tests | 14 passed |
| Full-map browser scenarios | 12 passed |
| Saved-filter/dashboard browser scenarios | 9 passed |
| Device-role filter browser scenarios | 6 passed |
| Device-role color/marker browser scenarios | 5 passed |
| Device-status/native-slug browser scenarios | 5 passed |
| Self-contained cache/initial-presentation browser scenarios | 13 passed |
| App/widget registration, installed imports, URL/template/static origins | Passed |
| System/static collection/dependency checks | Passed; 232 static files collected |
| Fresh migrations and isolated 4.7.4 upgrade | Passed; no pending migrations |
| Legacy-constraint repair using temporary tables | Passed for all six names and duplicate-constraint path |

The two additional GeoView integration tests cover ordered device choices with
role/status conditions and full, `brief` and explicit `fields` REST responses;
and replacing a device's tags while reusing map queries, choices and saved
widgets. The latter keeps the original tag assigned to another device because
NetBox intentionally excludes unused tags from its model-specific tag field.
The existing large tagged-object ID regression also passes with django-taggit 7.

The 37 installed-wheel browser checks exercise actual native selectors and
dashboard forms, saved filters, inclusion/exclusion, statuses, nested roles,
independent widgets, themed popups, marker colors/symbols/custom images,
desktop/mobile layouts, tile refresh/revalidation and live routing. The
Vienna–Linz car route returned 207.272 km, 141.3 minutes and 2,957 geometry
points; bicycle and pedestrian routes also passed. External routing data may
change independently. No uncaught JavaScript errors were reported. Light/dark
popup, widget and mobile screenshots were visually inspected.

The widget save scenario now submits invalid parameters, checks the rendered
error and retained slug, corrects the parameters and saves successfully. During
test development, Playwright's immediate manual slug fill raced the native
name-field blur handler, producing a duplicated value before submission. The
test now completes blur-driven generation first. The server's invalid-form
response was separately checked and preserves the submitted value correctly;
no runtime workaround was needed. Marker checks account for optional empty
symbols rather than assuming every configured role has one.

The 13 self-contained cache checks serve the checkout's real Leaflet/GeoView
assets with synthetic HTTP responses. They are counted separately from the
NetBox browser checks and do not demonstrate external service availability.

## Upstream review and targeted regressions

Sources: [official release notes](https://github.com/netbox-community/netbox/releases/tag/v4.7.5)
and [4.7.4–4.7.5 comparison](https://github.com/netbox-community/netbox/compare/v4.7.4...v4.7.5).

- The new REST ordering backend and changes to non-unique name/slug filters
  require no adaptation in GeoView's inherited `DeviceViewSet`. Narrow-response
  device choices, upstream count ordering and shared-name/shared-slug cases pass.
- Native forms now support a duplicate-submission guard on opted-in forms.
  GeoView's save/update workflow and corrected-error resubmission still work.
- Django, django-taggit, psycopg and GraphQL dependencies changed. The exact
  dependency set installs cleanly; tag changes, 64-bit tagged IDs, device
  serializers/config-context paths, selectors and app startup pass.
- The standard SSO pipeline now includes `auth_allowed`; custom pipelines
  omitting it warn that allowlists will not be enforced. Four upstream tests
  using a stand-in identity provider verify allowed, denied and existing users.
  This is not a test of a real SSO provider or the normal deployment's SSO setup.
- Region/site-group deletion and cached circuit ancestors changed. Three
  targeted upstream regressions verify preservation of indirect terminations
  and change logging, only in the disposable test database.

The upstream selection repeats the 31 selector, HTMX, dynamic-choice and device
config-context checks from the 4.7.4 report, then adds 17 tests: four allowlist
cases, one filter-constructor case, two count-ordering cases, seven shared
name/slug filter cases and three circuit-termination deletion cases. Exact labels
are retained in the validation directory's `upstream-labels.txt`.

## Database upgrade check

The dedicated 4.7.4 fixture database was copied before using 4.7.5. Its only
pending migrations were:

```text
circuits.0061_circuitterminations_cached_ancestors_on_delete
taggit.0007_alter_taggeditem_options
```

After migration, full-row hashes and counts of nine relevant tables matched
their before-upgrade snapshot exactly, including three sites, 16 devices, six
locations, eight device types and four custom fields. Region, site-group, tag
and saved-filter rows were also compared. This test uses synthetic fixtures,
not a production database copy.

NetBox also repairs historical auto-generated constraint names in
`dcim.0245_consolidate_unique_constraints`. A fresh database applies it normally;
an installation which already applied it does not rerun it during a 4.7.4 upgrade.
Its upstream repair SQL was additionally exercised against temporary tables in
the isolated upgrade database, covering all six legacy names and the case where
the replacement constraint already exists. Those temporary schema changes were
rolled back; public tables were not altered by that probe.

## Package checks, cleanup and limits

The final wheel and source distribution pass metadata validation. Tracked
runtime resources are compared byte-for-byte with the wheel, including compiled
translations, templates, static/vendor assets, management commands and fixture
JSON. Metadata declares Python >=3.12 and no additional runtime dependencies.
The source archive includes the validation documentation and regression tests.
The final release wheel is reinstalled and its integration suite is rerun after
documentation and release-note preparation; browser-tested runtime resources
remain identical. Release notes are validated from the dated 0.10.1 changelog.

Local source, configurations, runners, logs, snapshots and screenshots are
retained under `/home/prohph/geoview-netbox475-VQSlqhlv/`. Disposable browser
accounts use unusable passwords and private, short-lived sessions. Sessions and
owned saved filters/dashboards are removed after each suite; private session
files are removed. The temporary listener is stopped after validation. Isolated
databases and synthetic fixtures remain available for review.

The official source archive lacks generated documentation assets, producing the
existing `staticfiles.W004` warning. The inherited `LOGIN_REQUIRED` setting also
emits NetBox's deprecation warning. Neither affects plugin registration or tests.

This is a local compatibility and release-package check, not the complete
upstream NetBox suite, a production upgrade/restore, a load test, real-provider
SSO validation, or a Firefox/WebKit matrix. Use [TESTING.md](../../TESTING.md)
with the version's isolated source, pinned dependencies and dedicated database
to reproduce the suites. Future NetBox versions still require explicit testing.
