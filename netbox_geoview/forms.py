import json

from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.models import ObjectType
from dcim.choices import DeviceStatusChoices
from dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Manufacturer,
    Platform,
    Region,
    Site,
    SiteGroup,
)
from extras.models import SavedFilter
from tenancy.models import Tenant, TenantGroup
from users.models import Owner, OwnerGroup
from utilities.forms.fields import (
    DynamicModelMultipleChoiceField,
    QueryField,
    SlugField,
    TagFilterField,
)


from .filters import get_saved_filter_models as get_saved_filter_models
from .filters import get_usable_saved_filters, normalize_parameters


class GeoViewSavedFilterForm(forms.ModelForm):
    slug = SlugField(max_length=SavedFilter._meta.get_field("slug").max_length)
    parameters = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = SavedFilter
        fields = ("name", "slug", "description", "shared", "parameters")
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

    def clean_parameters(self):
        try:
            data = json.loads(self.cleaned_data["parameters"])
        except (TypeError, ValueError):
            raise forms.ValidationError(_("Invalid filter parameters.")) from None
        return dict(normalize_parameters(data, strict=True).lists())


class GeoViewFilterForm(forms.Form):
    model = Device

    q = QueryField(
        label=_("Search"),
        required=False,
    )
    filter_id = DynamicModelMultipleChoiceField(
        queryset=SavedFilter.objects.all(),
        required=False,
        label=_("Saved Filter"),
        query_params={"usable": True},
    )
    tag = TagFilterField(model)
    region = DynamicModelMultipleChoiceField(
        label=_("Region"),
        required=False,
        queryset=Region.objects.order_by("name"),
    )
    site_group = DynamicModelMultipleChoiceField(
        label=_("Site group"),
        required=False,
        queryset=SiteGroup.objects.order_by("name"),
    )
    site = DynamicModelMultipleChoiceField(
        label=_("Site"),
        required=False,
        queryset=Site.objects.order_by("name"),
        query_params={"region_id": "$region", "group_id": "$site_group"},
    )
    manufacturer = DynamicModelMultipleChoiceField(
        label=_("Manufacturer"),
        required=False,
        queryset=Manufacturer.objects.order_by("name"),
    )
    device_type = DynamicModelMultipleChoiceField(
        label=_("Model"),
        required=False,
        queryset=DeviceType.objects.order_by("model"),
        query_params={"manufacturer_id": "$manufacturer"},
    )
    platform = DynamicModelMultipleChoiceField(
        label=_("Operating system"),
        required=False,
        queryset=Platform.objects.order_by("name"),
        query_params={"manufacturer_id": "$manufacturer"},
    )
    role = DynamicModelMultipleChoiceField(
        label=_("Device roles"),
        required=False,
        queryset=DeviceRole.objects.all(),
    )
    status = forms.MultipleChoiceField(
        label=_("Status"),
        required=False,
        choices=DeviceStatusChoices,
    )
    tenant_group = DynamicModelMultipleChoiceField(
        label=_("Tenant group"),
        required=False,
        queryset=TenantGroup.objects.order_by("name"),
    )
    tenant = DynamicModelMultipleChoiceField(
        label=_("Tenant"),
        required=False,
        queryset=Tenant.objects.order_by("name"),
        query_params={"group_id": "$tenant_group"},
    )
    owner_group = DynamicModelMultipleChoiceField(
        label=_("Owner group"),
        required=False,
        queryset=OwnerGroup.objects.order_by("name"),
    )
    owner = DynamicModelMultipleChoiceField(
        label=_("Owner"),
        required=False,
        queryset=Owner.objects.order_by("name"),
        query_params={"group_id": "$owner_group"},
    )
    device = DynamicModelMultipleChoiceField(
        label=_("Device"),
        required=False,
        queryset=Device.objects.order_by("name"),
        query_params={
            "manufacturer_id": "$manufacturer",
            "device_type_id": "$device_type",
            "platform_id": "$platform",
            "geoview_role": "$role",
            "geoview_role_op": "$role_op",
            "geoview_status": "$status",
            "geoview_status_op": "$status_op",
            "tenant_group_id": "$tenant_group",
            "tenant_id": "$tenant",
            "owner_group_id": "$owner_group",
            "owner_id": "$owner",
        },
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["device"].widget.attrs["data-url"] = reverse(
            "plugins:netbox_geoview:device_choices"
        )
        if user is not None:
            for field in self.fields.values():
                queryset = getattr(field, "queryset", None)
                if queryset is not None and hasattr(queryset, "restrict"):
                    field.queryset = queryset.restrict(user, "view")
            self.fields["filter_id"].queryset = get_usable_saved_filters(user)
        object_type_ids = [
            ObjectType.objects.get_for_model(model).pk
            for model in get_saved_filter_models(self.data if self.is_bound else None)
        ]
        self.fields["filter_id"].widget.add_query_params(
            {"object_type_id": object_type_ids}
        )
