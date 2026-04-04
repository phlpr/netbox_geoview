from django import forms
from django.utils.translation import gettext_lazy as _

from dcim.models import Region, Site, SiteGroup
from utilities.forms.fields import DynamicModelMultipleChoiceField


class GeoViewFilterForm(forms.Form):
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
