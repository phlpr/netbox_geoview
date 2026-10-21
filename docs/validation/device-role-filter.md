# Device-role filter validation — 2026-10-21

This validates the development checkout based on GeoView 0.8.2 for
[issue #4](https://github.com/phlpr/netbox_geoview/issues/4). It is not a new
published release. Compatibility metadata remains 4.5.4–4.7.2.

## Results

| NetBox | Scope | Result |
|---|---|---|
| 4.5.10 | 13 new role-filter integration tests | 13 passed |
| 4.6.10 | 13 new role-filter integration tests | 13 passed |
| 4.7.0 | Complete GeoView integration suite | 81 passed, 1 expected skip |
| 4.7.2 | Complete GeoView integration suite | 82 passed |
| 4.7.0 | Chromium browser scenarios | 6 passed; no uncaught JavaScript errors |

All six lightweight utility/theme tests also passed. The expected 4.7.0 skip is
the existing Unicode-search regression for a core fix introduced in 4.7.1.
Source archives report the existing `staticfiles.W004` warning for missing
generated documentation assets. The 4.6/4.7 test configurations also emit the
existing `LOGIN_REQUIRED` deprecation warning.

## Behavior and integration coverage

- Role-only selection activates device markers, filter badges and saving.
- Selected roles include all descendants, using NetBox's existing
  `TreeNodeMultipleChoiceFilter` on both its older and newer tree backends.
- Exclusion removes complete selected subtrees. Multiple selected roles are
  alternatives; overlapping parent/child selections do not duplicate results.
- Site, manufacturer, model and explicit device conditions still constrain results.
- Empty roles yield an empty map. Invalid/inaccessible role IDs and invalid
  operators produce errors without falling back to a broader map.
- `role_id` is accepted as an alias for GeoView's canonical `role` parameter.
  Saved filters retain `role` and `role_op`, apply to Device and produce the
  same markers in the full map and dashboard widget.
- Saved filters reflect subsequent role hierarchy changes. Clearing an edited
  role does not reapply the old saved selection.
- Shared filters do not grant device permissions. Role choices and submitted
  roles respect the current user's NetBox role permissions.

The read-only `device-choices/` endpoint extends NetBox's native device list view
and keeps its serialization, pagination, ordinary filters and device permissions.
Its `geoview_role` and `geoview_role_op` parameters apply the same role helper as
the map. Native dynamic-select dependencies update results when either the roles
or the inclusion/exclusion operator changes. Anonymous requests redirect to
login, site-only viewers cannot list devices, and POST is not allowed.

## Browser and environment scope

The browser scenarios exercise the running local NetBox 4.7.0 with the separate
ten-device role-filter development data set. They check parent/grandchild
matching, immediate selector updates on exclusion, saving/reloading through the
UI, a native dashboard widget with identical results, multiple/empty roles and
390×844 mobile controls without horizontal overflow. Desktop filter, dashboard
and mobile screenshots were inspected. The local debug toolbar was collapsed
using its browser preference so it did not cover application controls.

Integration tests used dedicated databases, PostgreSQL 16, Redis test databases
14/15 and the retained version-specific environments described in the
[saved-filter/widget report](saved-filters-widgets.md). They did not seed or
migrate the normal development database. Browser authentication used a disposable
account with an unusable password; its session was revoked and its account,
saved filters and dashboard removed after validation.

Local browser artifacts are under
`/home/prohph/.local/share/netbox-geoview/issue-4/`. Run the deterministic role
integration cases with the commands in [TESTING.md](../../TESTING.md).
The complete upstream NetBox suite, all supported patch versions, other browsers
and load testing were not run. No plugin models, migrations or dependencies were
added, and no existing filter's matching semantics were changed.
