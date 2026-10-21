from django.urls import path

from .views import (
    GeoViewApplyFiltersView,
    GeoViewDeviceChoicesView,
    GeoViewFilterView,
    GeoViewMapView,
    GeoViewRouteView,
    GeoViewTileView,
    GeoViewMapDataView,
    GeoViewSaveFilterView,
)

app_name = "netbox_geoview"

urlpatterns = [
    path(
        "device-choices/",
        GeoViewDeviceChoicesView.as_view({"get": "list"}),
        name="device_choices",
    ),
    path("map-data/", GeoViewMapDataView.as_view(), name="map_data"),
    path("saved-filters/add/", GeoViewSaveFilterView.as_view(), name="savedfilter_add"),
    path("saved-filters/<int:pk>/edit/", GeoViewSaveFilterView.as_view(), name="savedfilter_edit"),
    path("", GeoViewMapView.as_view(), name="map"),
    path("filter/", GeoViewFilterView.as_view(), name="filter"),
    path("apply/", GeoViewApplyFiltersView.as_view(), name="apply"),
    path("route/", GeoViewRouteView.as_view(), name="route"),
    path(
        "tiles/<slug:layer_id>/<int:z>/<int:x>/<int:y>.png",
        GeoViewTileView.as_view(),
        name="tile",
    ),
]
