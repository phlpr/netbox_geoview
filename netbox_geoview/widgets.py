"""Native NetBox dashboard integration (4.5, 4.6 and 4.7)."""

from urllib.parse import urlencode

from django import forms
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
from extras.dashboard.utils import register_widget
from extras.dashboard.widgets import DashboardWidget, WidgetConfigForm
from extras.models import SavedFilter
from core.models import ObjectType
from dcim.models import Device, Site
from netbox.context import current_request
from utilities.forms.fields import DynamicModelChoiceField

from .permissions import can_view_geoview
from .filters import get_usable_saved_filters, normalize_parameters
from .version import __version__


@register_widget
class GeoViewMapWidget(DashboardWidget):
    default_title = _("GeoView map")
    description = _("Display a GeoView map using a saved filter.")
    width = 6
    height = 5
    default_config = {"fit_bounds": True}

    class ConfigForm(WidgetConfigForm):
        saved_filter_id = DynamicModelChoiceField(
            label=_("Saved filter"),
            queryset=SavedFilter.objects.none(),
            query_params={"usable": True},
            help_text=_(
                "Choose an enabled GeoView-compatible filter you own or which is shared."
            ),
        )
        fit_bounds = forms.BooleanField(
            label=_("Fit map to markers"), required=False, initial=True
        )

        def __init__(self, *args, **kwargs):
            # NetBox 4.5-4.7 does not pass request to widget forms. Its public
            # request ContextVar also scopes initial-choice labels and POSTs.
            request = kwargs.pop("request", None) or current_request.get()
            super().__init__(*args, **kwargs)
            if request is not None:
                self.fields["saved_filter_id"].queryset = (
                    get_usable_saved_filters(request.user)
                    .filter(
                        object_types__app_label="dcim",
                        object_types__model__in=("site", "device"),
                    )
                    .distinct()
                )
            self.fields["saved_filter_id"].widget.add_query_params(
                {
                    "object_type_id": [
                        ObjectType.objects.get_for_model(model).pk
                        for model in (Site, Device)
                    ],
                }
            )

        def clean_saved_filter_id(self):
            saved = self.cleaned_data["saved_filter_id"]
            normalize_parameters(saved.parameters, strict=True)
            if not saved.enabled:
                raise forms.ValidationError(_("The saved filter is disabled."))
            # NetBox stores widget configuration as JSON, not as model instances.
            return saved.pk

    def render(self, request):
        if not can_view_geoview(request.user):
            return str(_("You do not have permission to view GeoView."))
        query = urlencode(
            {
                "filter_id": self.config.get("saved_filter_id", ""),
                "fit_bounds": "1" if self.config.get("fit_bounds", True) else "0",
            }
        )
        return render_to_string(
            "netbox_geoview/widget.html",
            {
                "widget_id": self.id,
                "data_url": reverse("plugins:netbox_geoview:map_data") + "?" + query,
                "asset_version": f"{__version__}-widgets-1",
            },
            request=request,
        )
