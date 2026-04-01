from django import forms
from django.utils.translation import gettext_lazy as _

from dcim.models import Device, DeviceRole, Location, Site


class GeoViewFilterForm(forms.Form):
    q = forms.CharField(
        label=_("Search"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Device name, serial, asset tag"),
            }
        ),
    )
    sites = forms.ModelMultipleChoiceField(
        label=_("Sites"),
        required=False,
        queryset=Site.objects.none(),
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 8}),
    )
    locations = forms.ModelMultipleChoiceField(
        label=_("Locations"),
        required=False,
        queryset=Location.objects.none(),
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 8}),
    )
    device_roles = forms.ModelMultipleChoiceField(
        label=_("Device roles"),
        required=False,
        queryset=DeviceRole.objects.none(),
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 8}),
    )
    devices = forms.ModelMultipleChoiceField(
        label=_("Devices"),
        required=False,
        queryset=Device.objects.none(),
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 8}),
    )
    lat = forms.FloatField(
        label=_("Latitude"),
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "step": "0.000001"}
        ),
    )
    lon = forms.FloatField(
        label=_("Longitude"),
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "step": "0.000001"}
        ),
    )
    zoom = forms.IntegerField(
        label=_("Zoom"),
        required=False,
        min_value=1,
        max_value=19,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    limit = forms.IntegerField(
        label=_("Preview limit"),
        required=False,
        min_value=1,
        max_value=1000,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sites"].queryset = Site.objects.order_by("name")
        self.fields["locations"].queryset = Location.objects.order_by("name")
        self.fields["device_roles"].queryset = DeviceRole.objects.order_by("name")
        self.fields["devices"].queryset = Device.objects.order_by("name")
