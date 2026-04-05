from django import forms
from django.utils.translation import gettext_lazy as _

from core.models import ObjectType
from dcim.models import Device, DeviceType, Manufacturer, Platform, Region, Site, SiteGroup
from extras.models import SavedFilter
from tenancy.models import Tenant, TenantGroup
from users.models import Owner, OwnerGroup
from utilities.forms.fields import (
    DynamicModelMultipleChoiceField,
    QueryField,
    TagFilterField,
)


SITE_FILTER_FIELDS = ("region", "site_group", "site")
DEVICE_FILTER_FIELDS = (
    "q",
    "tag",
    "manufacturer",
    "device_type",
    "platform",
    "tenant_group",
    "tenant",
    "owner_group",
    "owner",
    "device",
)


def _has_filter_value(source, field_name):
    if source is None:
        return False
    if hasattr(source, "getlist"):
        values = source.getlist(field_name)
        return any(str(value).strip() for value in values)
    value = source.get(field_name)
    if value is None:
        return False
    if hasattr(value, "exists"):
        return value.exists()
    if isinstance(value, (list, tuple, set)):
        return bool(value)
    return bool(str(value).strip())


def get_saved_filter_models(source=None):
    models = []
    if any(_has_filter_value(source, field) for field in SITE_FILTER_FIELDS):
        models.append(Site)
    if any(_has_filter_value(source, field) for field in DEVICE_FILTER_FIELDS):
        models.append(Device)
    if models:
        return models
    return [Site, Device]


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
            "tenant_group_id": "$tenant_group",
            "tenant_id": "$tenant",
            "owner_group_id": "$owner_group",
            "owner_id": "$owner",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        object_type_ids = [
            ObjectType.objects.get_for_model(model).pk
            for model in get_saved_filter_models(self.data if self.is_bound else None)
        ]
        self.fields["filter_id"].widget.add_query_params(
            {"object_type_id": object_type_ids}
        )
