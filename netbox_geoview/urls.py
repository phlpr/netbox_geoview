from django.urls import path

from .views import GeoViewFilterView, GeoViewMapView, GeoViewTileView

app_name = "netbox_geoview"

urlpatterns = [
    path("", GeoViewMapView.as_view(), name="map"),
    path("filter/", GeoViewFilterView.as_view(), name="filter"),
    path("tiles/<int:z>/<int:x>/<int:y>.png", GeoViewTileView.as_view(), name="tile"),
]
