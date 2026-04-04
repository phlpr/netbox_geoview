from django.utils.translation import gettext_lazy as _

from netbox.plugins import PluginMenu, PluginMenuItem


menu = PluginMenu(
    label=_("Geo-View"),
    groups=(
        (
            _("Navigation"),
            (
                PluginMenuItem(
                    link="plugins:netbox_geoview:map",
                    link_text=_("Map"),
                ),
            ),
        ),
    ),
    icon_class="mdi mdi-map-marker-radius-outline",
)
