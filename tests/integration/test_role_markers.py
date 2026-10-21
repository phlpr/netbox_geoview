"""Role colors and explicit marker overrides on maps and dashboard widgets."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import ObjectType
from dcim.models import Device, DeviceRole, Site
from extras.models import SavedFilter

from netbox_geoview.services.maps import GeoViewMapService


@override_settings(PLUGINS_CONFIG={"netbox_geoview": {}})
class DeviceRoleMarkerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_geoview_testdata", stdout=StringIO())
        cls.admin = get_user_model().objects.create_superuser(
            username="role-marker-admin", password="test-only"
        )
        cls.site = Site.objects.get(slug="geoview-vienna-dc")
        cls.role = DeviceRole.objects.get(slug="geoview-core-router")
        cls.role.color = "123abc"
        cls.role.save()

    def setUp(self):
        self.client.force_login(self.admin)
        self.map_url = reverse("plugins:netbox_geoview:map")
        self.base_config = {
            "site_marker": {"color": "#112233", "symbol": "SITE"},
            "site_group_markers": {
                self.site.group.slug: {"color": "#334455", "symbol": "GROUP"}
            },
        }

    def markers(self, config, parameters=None):
        with override_settings(PLUGINS_CONFIG={"netbox_geoview": config}):
            response = self.client.get(self.map_url, parameters or {"q": "geoview"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["filter_form"].errors)
        return {marker["name"]: marker for marker in response.context["map_config"]["site_markers"]}

    def test_missing_or_false_switch_keeps_existing_site_group_style(self):
        for switch in ({}, {"use_role_colors": False}):
            with self.subTest(switch=switch):
                markers = self.markers({**self.base_config, **switch})
                self.assertTrue(markers)
                self.assertTrue(all(marker["marker_style"]["color"] == "#334455"
                                    for marker in markers.values()))
                self.assertTrue(all(marker["marker_style"]["symbol"] == "GROUP"
                                    for marker in markers.values()))

    def test_role_colors_change_device_pins_and_leave_site_markers_unchanged(self):
        markers = self.markers(
            {**self.base_config, "use_role_colors": True},
            {"site": self.site.pk, "q": "geoview"},
        )
        self.assertEqual(markers[self.site.name]["marker_style"]["color"], "#334455")
        self.assertEqual(markers["gv-vie-core-01"]["marker_style"]["color"], "#123abc")
        self.assertEqual(markers["gv-vie-access-01"]["marker_style"]["color"], "#2196f3")
        self.assertEqual(markers["gv-vie-core-01"]["marker_style"]["symbol"], "GROUP")

    def test_only_boolean_true_enables_automatic_role_colors(self):
        for value in ("false", "true", "False", 1, None):
            with self.subTest(value=value):
                markers = self.markers({**self.base_config, "use_role_colors": value})
                self.assertEqual(markers["gv-vie-core-01"]["marker_style"]["color"], "#334455")

    def test_explicit_role_color_and_symbol_override_both_switch_modes(self):
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                markers = self.markers({
                    **self.base_config,
                    "use_role_colors": enabled,
                    "device_role_markers": {
                        self.role.slug: {"color": "#abcdef", "symbol": "R"}
                    },
                })
                self.assertEqual(markers["gv-vie-core-01"]["marker_style"]["color"], "#abcdef")
                self.assertEqual(markers["gv-vie-core-01"]["marker_style"]["symbol"], "R")
                self.assertEqual(markers["gv-vie-access-01"]["marker_style"]["color"],
                                 "#2196f3" if enabled else "#334455")

    def test_role_override_matches_id_then_slug_then_name_case_insensitively(self):
        for key in (self.role.pk, str(self.role.pk)):
            cases = (
                ({self.role.name: {"symbol": "NAME"}, self.role.slug: {"symbol": "SLUG"},
                  key: {"symbol": "ID"}}, "ID"),
                ({self.role.name: {"symbol": "NAME"},
                  f" {self.role.slug.upper()} ": {"symbol": "SLUG"}}, "SLUG"),
                ({f" {self.role.name.upper()} ": {"symbol": "NAME"}}, "NAME"),
            )
            for overrides, expected in cases:
                with self.subTest(key=key, expected=expected):
                    markers = self.markers({**self.base_config, "device_role_markers": overrides})
                    self.assertEqual(markers["gv-vie-core-01"]["marker_style"]["symbol"], expected)

    def test_custom_role_image_keeps_its_dimensions_and_anchor_points(self):
        custom = {
            "icon_url": "/static/custom/router.svg", "icon_size": [32, 48],
            "icon_anchor": [16, 48], "popup_anchor": [0, -42],
        }
        markers = self.markers({
            **self.base_config, "use_role_colors": True,
            "device_role_markers": {self.role.slug: custom},
        })
        style = markers["gv-vie-core-01"]["marker_style"]
        self.assertEqual({key: style[key] for key in custom}, custom)
        self.assertEqual(style["color"], "#123abc")
        self.assertEqual(markers["gv-vie-access-01"]["marker_style"]["icon_url"], "")

    def test_partial_overrides_inherit_marker_options_and_can_clear_an_image(self):
        config = {
            **self.base_config, "use_role_colors": True,
            "site_marker": {"icon_url": "/static/custom/site.svg", "icon_size": [36, 44]},
            "device_role_markers": {self.role.slug: {"symbol": "R", "icon_url": ""}},
        }
        markers = self.markers(config)
        core = markers["gv-vie-core-01"]["marker_style"]
        access = markers["gv-vie-access-01"]["marker_style"]
        self.assertEqual(core["icon_url"], "")
        self.assertEqual(core["symbol"], "R")
        self.assertEqual(core["color"], "#123abc")
        self.assertEqual(core["icon_size"], [36, 44])
        self.assertEqual(access["icon_url"], "/static/custom/site.svg")

    def test_parent_marker_overrides_do_not_replace_a_child_roles_own_style(self):
        parent = DeviceRole.objects.create(name="Network", slug="network", color="654321")
        self.role.parent = parent
        self.role.save()
        markers = self.markers({
            **self.base_config, "use_role_colors": True,
            "device_role_markers": {parent.slug: {"color": "#ffffff", "symbol": "P"}},
        })
        self.assertEqual(markers["gv-vie-core-01"]["marker_style"]["color"], "#123abc")
        self.assertEqual(markers["gv-vie-core-01"]["marker_style"]["symbol"], "GROUP")

    def test_invalid_legacy_role_colors_fall_back_to_configured_marker_color(self):
        for value in ("", "zzzzzz"):
            with self.subTest(value=value):
                DeviceRole.objects.filter(pk=self.role.pk).update(color=value)
                markers = self.markers({**self.base_config, "use_role_colors": True})
                self.assertEqual(markers["gv-vie-core-01"]["marker_style"]["color"], "#334455")

    def test_non_dictionary_role_overrides_are_ignored(self):
        for value in (None, [], "bad", {self.role.slug: "bad"}):
            with self.subTest(value=value):
                markers = self.markers({
                    **self.base_config, "use_role_colors": True, "device_role_markers": value
                })
                self.assertEqual(markers["gv-vie-core-01"]["marker_style"]["color"], "#123abc")

    def test_saved_filter_widget_and_full_map_use_identical_role_markers(self):
        saved = SavedFilter.objects.create(
            name="Marker widget", slug="marker-widget", user=self.admin,
            parameters={"q": "geoview"},
        )
        saved.object_types.add(ObjectType.objects.get_for_model(Device))
        config = {
            **self.base_config, "use_role_colors": True,
            "device_role_markers": {
                self.role.slug: {"color": "#abcdef", "icon_url": "/static/custom/router.svg"}
            },
        }
        with override_settings(PLUGINS_CONFIG={"netbox_geoview": config}):
            page = self.client.get(self.map_url, {"filter_id": saved.pk})
            data = self.client.get(reverse("plugins:netbox_geoview:map_data"), {"filter_id": saved.pk})
        self.assertEqual(data.status_code, 200)
        self.assertEqual(page.context["map_config"]["site_markers"], data.json()["config"]["site_markers"])
        self.assertEqual(len(data.json()["config"]["site_markers"]), 6)

    def test_styles_use_preloaded_role_and_site_data_without_extra_queries(self):
        devices = list(Device.objects.select_related("role", "site__group"))
        service = GeoViewMapService()
        with override_settings(PLUGINS_CONFIG={"netbox_geoview": {"use_role_colors": True}}):
            with self.assertNumQueries(0):
                styles = [service.get_device_marker_style(device) for device in devices]
        self.assertEqual(len(styles), 6)
