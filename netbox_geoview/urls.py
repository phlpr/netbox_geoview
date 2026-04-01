from django.urls import path

from .views import GeoViewFilterView, GeoViewMapView

app_name = "netbox_geoview"

urlpatterns = [
    path("", GeoViewMapView.as_view(), name="map"),
    path("filter/", GeoViewFilterView.as_view(), name="filter"),
]
