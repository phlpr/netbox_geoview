# Reusable GeoView Test Data

The repository includes an idempotent NetBox management command and a JSON
data definition for local GeoView development.

> [!WARNING]
> Use this command only with development or test databases. It writes sites,
> locations, device types, roles, devices, and custom fields to the configured
> NetBox database.

## Load or refresh the data

Run this from the NetBox checkout with its virtual environment active:

```bash
python manage.py seed_geoview_testdata
```

Running the command repeatedly updates the same prefixed objects rather than
creating duplicates.

The complete operation runs in one database transaction. Invalid input or a
validation error rolls back the current run.

## Use a modified local data file

Copy or edit `netbox_geoview/testdata/geoview_seed_data.json`, then run:

```bash
python manage.py seed_geoview_testdata \
  --data-file /absolute/path/to/geoview_seed_data.json
```

The default data set creates three Austrian sites, six nested locations, four
device types, four roles, six devices, and four custom fields. Some devices
have their own coordinates while others deliberately inherit the coordinates
of their site, covering both GeoView coordinate paths.
