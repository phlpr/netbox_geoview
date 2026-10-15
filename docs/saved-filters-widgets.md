# Saved filters and dashboard maps

This feature is available in the development checkout, not in the published
GeoView 0.8.2 package. It uses NetBox's existing SavedFilter and Dashboard models;
there are no GeoView database models or migrations.

## Save and reuse a map selection

1. Open GeoView and use the Filter tab to select sites or devices and operators.
2. Apply the conditions. On the Map tab, choose **Save filter**.
3. Enter a unique name and slug and, optionally, a description. Sharing is off by
   default. Submit the form to return to the map using the new filter.
4. To reuse it, select it in **Saved Filter** and press **Load filter**. Its
   conditions and operators populate the editable filter controls.
5. After changing and applying conditions, use **Update saved filter** to replace
   your filter's conditions, or **Save as new filter** to create an independent copy.

Loading saved filters and applying edited conditions use separate forms. Clearing
an edited condition therefore does not silently reapply the old saved value.
An update keeps the filter ID and affects widgets which reference it on their
next refresh. A copy receives its own ID and does not affect existing widgets.

When combining multiple saved filters, the map offers a copy rather than updating
one of the inputs. Saving resolves references to accessible filters and stores the
effective conditions; subsequent edits to the input filters do not alter this copy.
Existing ID (`?filter_id=42`) and slug (`?filter=example`) links remain supported.

## Add a dashboard widget

1. On your NetBox dashboard, add a widget and choose **GeoView map**.
2. Choose an enabled saved filter which you own or which is shared with you.
3. Set a title and choose whether to fit the map to its markers.
4. Save, unlock the dashboard if needed, and position or resize the widget.

Each widget stores the saved filter's ID and its own display settings in your
NetBox dashboard configuration. Renaming a filter does not break the reference.
Multiple widgets can show different filters or different views of the same filter.
The default widget is six columns wide and five dashboard rows high.
The toolbar wraps in narrow cards. With automatic bounds enabled, resizing the
widget also refits its markers; otherwise the current map center is preserved.

The widget offers pan/zoom, map layers, themed popups, **Refresh** and
**Open in GeoView**. Mouse-wheel zoom is disabled to keep dashboard scrolling
usable. Routing and distance measurement are available in the full GeoView page,
not in the initial widget. There is no periodic polling: data is fetched when the
dashboard opens and when Refresh is pressed. Without automatic bounds, the map
starts at the instance's configured GeoView center and zoom.
While a popup is open, compact widgets temporarily hide the top map controls so
they do not cover its content or close button. Attribution remains visible.

## Conditions and matching

Supported conditions are search, tags, region, site group, site, manufacturer,
device type, platform, tenant group, tenant, owner group, owner and device.
List selections support inclusion (`exact`) and exclusion (`n`). Multiple values
within a normal selection are alternatives; different conditions are combined.
Tags retain GeoView's existing all-selected-tags behavior and untagged support.

Site conditions select site markers. Device conditions select device markers.
When both are present, device results are also constrained to the selected sites.
Objects without usable coordinates are omitted. Devices use their own coordinates,
falling back to site coordinates, as in the existing full map.

Saved filters use GeoView's parameter names, for example:

```json
{
  "site": [12],
  "site_op": ["exact"],
  "manufacturer": [3],
  "manufacturer_op": ["n"]
}
```

Common NetBox ID aliases such as `site_id`, `region_id` and `manufacturer_id`
are accepted. This is not a general NetBox filter engine: conditions such as
`status`, arbitrary lookups and `cf_*` custom-field filters are unsupported.
An incompatible saved filter yields an explicit error and no marker data.
Legacy saved `lat`, `lon` and `zoom` keys are ignored and omitted when saving.

Explicit URL conditions override the corresponding saved conditions. Multiple
saved filters combine values, but conflicting operators and circular references
are rejected. The widget selects exactly one saved filter; the full map may load
several. These are live database queries, not snapshots of device IDs.

## Access and sharing

GeoView's login and existing Site-or-Device view permission requirement applies
to the full map, widgets, JSON data, tiles and routing. Filter expansion additionally
requires an enabled SavedFilter accessible through NetBox's view permissions and
owned by the current user or marked shared. Sharing a filter does not grant access
to the sites, devices or related filter choices it selects.

Creating or copying requires `extras.add_savedfilter`. Updating requires
`extras.change_savedfilter`, matching NetBox object constraints, and ownership;
superusers may update another user's filter. POST requests require CSRF protection.
NetBox's standard Saved Filters screens remain available for managing records.

The JSON endpoint checks current permissions on every request and is not cached
across users. Removing sharing, disabling/deleting a filter or losing access shows
an unavailable message on refresh; it does not substitute all objects. Valid
filters with zero matching geolocated objects show an empty map instead.
The standard NetBox `shared` setting controls filter usability, not secret storage;
do not put credentials in filter parameters.

## Implementation and validation

`filters.py` owns normalization, accessible reference resolution, operators and
serialization. `services/maps.py` shares settings, restricted queries, coordinates
and popup/marker preparation between page views and widget data requests.
`widgets.py` uses NetBox's native DashboardWidget/WidgetConfigForm API and registers
through PluginConfig.ready(). Widget configuration contains JSON scalar values.
Because these NetBox versions do not pass a user argument to widget forms, the
form uses NetBox's public current-request context to restrict both initial labels
and submitted filter IDs. Without a request it exposes no filter choices.

The existing map renderer manages per-element instances. The widget loader loads
Leaflet/CSS/JavaScript once, fetches data from `map-data/`, handles HTMX lifecycle
and manual refresh, and removes old data before a new request. ResizeObserver
keeps Leaflet aligned with dashboard sizing. No iframe or NetBox template override
is needed. See [TESTING.md](../TESTING.md) for validation commands and reports.
