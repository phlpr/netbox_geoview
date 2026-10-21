"""Device-role filtering across the map, selectors, saved filters and widgets."""

import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.models import ObjectType
from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from extras.models import SavedFilter
from users.models import ObjectPermission

from netbox_geoview.widgets import GeoViewMapWidget


class DeviceRoleFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_geoview_testdata", stdout=StringIO())
        cls.admin = get_user_model().objects.create_superuser(
            username="role-admin", password="test-only"
        )
        cls.switch = DeviceRole.objects.create(name="Switch", slug="role-test-switch")
        cls.access = DeviceRole.objects.get(slug="geoview-access-switch")
        cls.access.parent = cls.switch
        cls.access.save()
        cls.campus = DeviceRole.objects.create(
            name="Campus", slug="role-test-campus", parent=cls.access
        )
        cls.distribution = DeviceRole.objects.create(
            name="Distribution", slug="role-test-distribution", parent=cls.switch
        )
        cls.empty = DeviceRole.objects.create(name="Empty", slug="role-test-empty")
        cls.direct = Device.objects.get(name="gv-vie-core-01")
        cls.direct.role = cls.switch
        cls.direct.save()
        cls.child = Device.objects.get(name="gv-vie-access-01")
        cls.grandchild = Device.objects.get(name="gv-graz-access-01")
        cls.grandchild.role = cls.campus
        cls.manufacturer = Manufacturer.objects.create(
            name="Alternate hardware", slug="role-test-alternate"
        )
        alternate = DeviceType.objects.create(
            manufacturer=cls.manufacturer, model="Alternate switch", slug="alternate-switch"
        )
        cls.grandchild.device_type = alternate
        cls.grandchild.platform = None
        cls.grandchild.save()
        cls.distributed = Device.objects.get(name="gv-linz-core-01")
        cls.distributed.role = cls.distribution
        cls.distributed.save()
        cls.firewall = Device.objects.get(name="gv-graz-fw-01")
        cls.sensor = Device.objects.get(name="gv-linz-sensor-01")

    def setUp(self):
        self.client.force_login(self.admin)
        self.map_url = reverse("plugins:netbox_geoview:map")
        self.choices_url = reverse("plugins:netbox_geoview:device_choices")
        self.data_url = reverse("plugins:netbox_geoview:map_data")
        self.save_url = reverse("plugins:netbox_geoview:savedfilter_add")

    def marker_names(self, response, *, widget=False):
        config = response.json()["config"] if widget else response.context["map_config"]
        return {
            marker["name"] for marker in config["site_markers"]
            if marker["object_type"] == "device"
        }

    def saved(self, parameters, **kwargs):
        saved = SavedFilter.objects.create(
            name="Role filter", slug="role-filter", user=self.admin,
            parameters=parameters, **kwargs,
        )
        saved.object_types.add(ObjectType.objects.get_for_model(Device))
        return saved

    def grant(self, user, model, **constraints):
        permission = ObjectPermission.objects.create(
            name=f"Role test {model.__name__}", actions=["view"], constraints=constraints
        )
        permission.object_types.add(ObjectType.objects.get_for_model(model))
        permission.users.add(user)

    def test_role_only_includes_direct_child_and_grandchild_devices(self):
        page = self.client.get(self.map_url, {"role": self.switch.pk})
        self.assertEqual(page.status_code, 200)
        self.assertFalse(page.context["filter_form"].errors)
        self.assertEqual(self.marker_names(page), {
            self.direct.name, self.child.name, self.grandchild.name, self.distributed.name
        })
        self.assertEqual(page.context["active_filter_count"], 1)
        self.assertEqual(page.context["active_filter_badges"], ["Device roles is: Switch"])
        self.assertTrue(page.context["save_filter_url"])
        self.assertContains(page, 'name="role_op"')
        self.assertContains(page, 'name="role"')
        self.assertContains(page, self.choices_url)

    def test_multiple_roles_are_alternatives_and_overlapping_trees_do_not_duplicate(self):
        for selected, expected in (
            ([self.access, self.firewall.role], {self.child.name, self.grandchild.name, self.firewall.name}),
            ([self.switch, self.access], {
                self.direct.name, self.child.name, self.grandchild.name, self.distributed.name
            }),
        ):
            with self.subTest(roles=selected):
                page = self.client.get(self.map_url, {"role": [role.pk for role in selected]})
                self.assertEqual(self.marker_names(page), expected)
                self.assertEqual(page.context["selection_counts"]["devices"], len(expected))

    def test_exclusion_removes_entire_role_subtrees(self):
        for selected, expected in (
            ([self.switch], {self.firewall.name, self.sensor.name}),
            ([self.access, self.firewall.role], {self.direct.name, self.distributed.name, self.sensor.name}),
        ):
            with self.subTest(roles=selected):
                page = self.client.get(self.map_url, {
                    "role": [role.pk for role in selected], "role_op": "n"
                })
                self.assertEqual(self.marker_names(page), expected)
                self.assertEqual(page.context["filter_ops"]["role"], "n")

    def test_empty_role_has_no_results_and_excluding_it_keeps_all_devices(self):
        page = self.client.get(self.map_url, {"role": self.empty.pk})
        self.assertEqual(self.marker_names(page), set())
        self.assertFalse(page.context["filter_form"].errors)
        page = self.client.get(self.map_url, {"role": self.empty.pk, "role_op": "n"})
        self.assertEqual(len(self.marker_names(page)), 6)

    def test_role_combines_with_site_hardware_and_explicit_device_filters(self):
        for additional, expected in (
            ({"site": self.direct.site_id}, {self.direct.name, self.child.name}),
            ({"manufacturer": self.manufacturer.pk}, {self.grandchild.name}),
            ({"device_type": self.direct.device_type_id}, {self.direct.name, self.distributed.name}),
            ({"device": self.firewall.pk}, set()),
        ):
            with self.subTest(additional=additional):
                page = self.client.get(self.map_url, {"role": self.switch.pk, **additional})
                self.assertEqual(self.marker_names(page), expected)

    def test_device_choices_follow_role_operator_and_other_native_filters(self):
        cases = (
            ({"geoview_role": self.switch.pk}, {
                self.direct.name, self.child.name, self.grandchild.name, self.distributed.name
            }),
            ({"geoview_role": self.switch.pk, "geoview_role_op": "n"}, {self.firewall.name, self.sensor.name}),
            ({"geoview_role": [self.access.pk, self.firewall.role_id]}, {
                self.child.name, self.grandchild.name, self.firewall.name
            }),
            ({"geoview_role": self.switch.pk, "manufacturer_id": self.manufacturer.pk}, {self.grandchild.name}),
            ({"geoview_role": self.empty.pk}, set()),
            ({"q": "gv-vie"}, {self.direct.name, self.child.name}),
        )
        for parameters, expected in cases:
            with self.subTest(parameters=parameters):
                choices = self.client.get(self.choices_url, parameters)
                self.assertEqual(choices.status_code, 200)
                self.assertEqual({row["name"] for row in choices.json()["results"]}, expected)
        self.assertEqual(self.client.post(self.choices_url, {}).status_code, 405)

    def test_saved_role_id_alias_round_trip_and_widget_match_the_map(self):
        response = self.client.post(self.save_url, {
            "name": "Excluded switches", "slug": "excluded-switches",
            "parameters": json.dumps({"role_id": [self.switch.pk], "role_op": "n"}),
        })
        self.assertEqual(response.status_code, 302)
        saved = SavedFilter.objects.get(slug="excluded-switches")
        self.assertEqual(saved.parameters, {"role": [str(self.switch.pk)], "role_op": ["n"]})
        self.assertEqual(
            list(saved.object_types.values_list("pk", flat=True)),
            [ObjectType.objects.get_for_model(Device).pk],
        )
        page = self.client.get(response.url)
        data = self.client.get(self.data_url, {"filter_id": saved.pk})
        self.assertEqual(data.status_code, 200)
        self.assertEqual(self.marker_names(page), {self.firewall.name, self.sensor.name})
        self.assertEqual(self.marker_names(page), self.marker_names(data, widget=True))
        request = RequestFactory().get("/")
        request.user = self.admin
        config = GeoViewMapWidget.ConfigForm({"saved_filter_id": saved.pk}, request=request)
        self.assertTrue(config.is_valid(), config.errors)
        self.assertEqual(config.cleaned_data["saved_filter_id"], saved.pk)

    def test_saved_role_filter_tracks_hierarchy_changes(self):
        saved = self.saved({"role": [self.switch.pk]})
        self.campus.parent = self.firewall.role
        self.campus.save()
        data = self.client.get(self.data_url, {"filter_id": saved.pk})
        self.assertEqual(data.status_code, 200)
        self.assertEqual(self.marker_names(data, widget=True), {
            self.direct.name, self.child.name, self.distributed.name
        })

    def test_role_id_url_alias_and_clearing_a_saved_role(self):
        page = self.client.get(self.map_url, {"role_id": self.campus.pk})
        self.assertEqual(self.marker_names(page), {self.grandchild.name})
        saved = self.saved({"role": [self.switch.pk]})
        page = self.client.get(self.map_url, {
            "source_filter_id": saved.pk, "q": self.firewall.name
        })
        self.assertEqual(self.marker_names(page), {self.firewall.name})
        self.assertNotIn("role=", page.context["save_filter_url"])

    def test_invalid_roles_and_operators_do_not_broaden_results(self):
        for conditions in ({"role": "missing"}, {"role": 999999999},
                           {"role": self.switch.pk, "role_op": "bad"}):
            with self.subTest(conditions=conditions):
                page = self.client.get(self.map_url, conditions)
                self.assertTrue(page.context["filter_form"].errors)
                self.assertEqual(self.marker_names(page), set())
                saved = self.saved(conditions)
                self.assertEqual(self.client.get(self.data_url, {"filter_id": saved.pk}).status_code, 400)
                saved.delete()
                choices = self.client.get(self.choices_url, {
                    "geoview_role": conditions["role"],
                    "geoview_role_op": conditions.get("role_op", "exact"),
                })
                self.assertEqual(choices.status_code, 400)

    def test_shared_role_filters_and_selectors_respect_device_constraints(self):
        saved = self.saved({"role": [self.switch.pk]}, shared=True)
        user = get_user_model().objects.create_user(username="role-constrained")
        self.grant(user, Device, pk=self.grandchild.pk)
        self.grant(user, DeviceRole, pk=self.switch.pk)
        self.grant(user, SavedFilter)
        self.client.force_login(user)
        page = self.client.get(self.map_url, {"role": self.switch.pk})
        self.assertEqual(self.marker_names(page), {self.grandchild.name})
        choices = self.client.get(self.choices_url, {"geoview_role": self.switch.pk})
        self.assertEqual(choices.status_code, 200)
        self.assertEqual([row["name"] for row in choices.json()["results"]], [self.grandchild.name])
        data = self.client.get(self.data_url, {"filter_id": saved.pk})
        self.assertEqual(data.status_code, 200)
        self.assertEqual(self.marker_names(data, widget=True), {self.grandchild.name})
        roles = self.client.get(reverse("dcim-api:devicerole-list"))
        self.assertEqual([row["id"] for row in roles.json()["results"]], [self.switch.pk])

    def test_inaccessible_roles_are_rejected_on_map_selector_and_widget(self):
        saved = self.saved({"role": [self.switch.pk]}, shared=True)
        user = get_user_model().objects.create_user(username="role-inaccessible")
        self.grant(user, Device)
        self.grant(user, DeviceRole, pk=self.access.pk)
        self.grant(user, SavedFilter)
        self.client.force_login(user)
        page = self.client.get(self.map_url, {"role": self.switch.pk})
        self.assertTrue(page.context["filter_form"].errors)
        self.assertEqual(self.marker_names(page), set())
        self.assertEqual(self.client.get(self.choices_url, {"geoview_role": self.switch.pk}).status_code, 400)
        self.assertEqual(self.client.get(self.data_url, {"filter_id": saved.pk}).status_code, 400)

    def test_device_choices_require_login_and_native_device_view_permission(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.choices_url).status_code, 302)
        user = get_user_model().objects.create_user(username="roles-site-only")
        self.grant(user, Site)
        self.grant(user, DeviceRole)
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.choices_url).status_code, 403)
