from django.utils.translation import gettext_lazy as _

from netbox.context import current_request
from netbox.plugins import PluginMenu, PluginMenuItem

from .permissions import can_view_geoview


class GeoViewMenu(PluginMenu):
    @property
    def groups(self):
        # NetBox ANDs item.permissions. Filter this menu with the same OR check
        # as the views, using request-local context rather than cached user state.
        request = current_request.get()
        if request is None or not can_view_geoview(request.user):
            return ()
        return self._groups

    @groups.setter
    def groups(self, value):
        self._groups = value


menu = GeoViewMenu(
    label=_("Geo-View"),
    groups=(
        (
            _("Navigation"),
            (
                PluginMenuItem(
                    link="plugins:netbox_geoview:map",
                    link_text=_("Map"),
                    auth_required=True,
                ),
            ),
        ),
    ),
    icon_class="mdi mdi-map-marker-radius-outline",
)
