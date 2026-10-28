"""Device status matching across the map, device choices and saved widgets."""

import json
from io import StringIO
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse
from core.models import ObjectType
from dcim.models import Device
from extras.models import SavedFilter
from users.models import ObjectPermission

from netbox_geoview.widgets import GeoViewMapWidget


class DeviceStatusFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_geoview_testdata", stdout=StringIO())
        cls.admin = get_user_model().objects.create_superuser(username="status-admin")
        devices = list(Device.objects.order_by("name"))
        Device.objects.all().update(status="active")
        cls.offline, cls.planned = devices[:2]
        Device.objects.filter(pk=cls.offline.pk).update(status="offline")
        Device.objects.filter(pk=cls.planned.pk).update(status="planned")
        cls.active_names = {device.name for device in devices[2:]}

    def setUp(self):
        self.client.force_login(self.admin)
        self.map_url = reverse("plugins:netbox_geoview:map")
        self.choices_url = reverse("plugins:netbox_geoview:device_choices")
        self.save_url = reverse("plugins:netbox_geoview:savedfilter_add")
        self.data_url = reverse("plugins:netbox_geoview:map_data")

    def post_filter(self, parameters):
        return self.client.post(self.save_url, {
            "name": "Offline devices", "slug": "offline-devices",
            "parameters": json.dumps(parameters),
        })

    def test_status_only_multiple_and_excluded_statuses(self):
        for statuses, operator, expected in (
            (["offline"], "exact", {self.offline.name}),
            (["offline", "planned"], "exact", {self.offline.name, self.planned.name}),
            (["offline", "planned"], "n", self.active_names),
            (["active", "offline", "planned"], "n", set()),
        ):
            with self.subTest(statuses=statuses, operator=operator):
                page = self.client.get(self.map_url, {"status": statuses, "status_op": operator})
                self.assertEqual(page.status_code, 200)
                self.assertFalse(page.context["filter_form"].errors)
                self.assertEqual(page.context["selection_counts"], {"sites": 0, "devices": len(expected)})
                self.assertEqual(
                    {marker["name"] for marker in page.context["map_config"]["site_markers"]}, expected
                )
                self.assertEqual(page.context["active_filter_count"], 1)
                self.assertTrue(page.context["save_filter_url"])
                group = page.context["selection_groups"][0]
                self.assertEqual(group["operator"], operator)
                self.assertEqual(group["entries"], [value.title() for value in statuses])

    def test_status_combines_with_site_role_hardware_and_explicit_device(self):
        parameters = {
            "site": self.offline.site_id,
            "manufacturer": self.offline.device_type.manufacturer_id,
            "role": self.offline.role_id,
            "device": self.offline.pk,
            "status": "offline",
        }
        for operator, expected in (("exact", 1), ("n", 0)):
            page = self.client.get(self.map_url, parameters | {"status_op": operator})
            self.assertFalse(page.context["filter_form"].errors)
            self.assertEqual(page.context["selection_counts"]["devices"], expected)

    def test_device_selector_follows_status_and_operator(self):
        for operator, expected in (
            ("exact", {self.offline.pk, self.planned.pk}),
            ("n", set(Device.objects.filter(status="active").values_list("pk", flat=True))),
        ):
            response = self.client.get(self.choices_url, {
                "geoview_status": ["offline", "planned"], "geoview_status_op": operator,
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual({row["id"] for row in response.json()["results"]}, expected)
        page = self.client.get(self.map_url)
        self.assertContains(page, 'geoview_status')
        self.assertContains(page, 'geoview_status_op')

    def test_saved_status_round_trip_apply_and_widget(self):
        parameters = {"status": ["active", "planned"], "status_op": "n"}
        response = self.post_filter(parameters)
        self.assertEqual(response.status_code, 302)
        saved = SavedFilter.objects.get(slug="offline-devices")
        self.assertEqual(saved.parameters, {"status": ["active", "planned"], "status_op": ["n"]})
        self.assertEqual(
            list(saved.object_types.values_list("pk", flat=True)),
            [ObjectType.objects.get_for_model(Device).pk],
        )
        for reference in ({"filter_id": saved.pk}, {"filter": saved.slug}):
            page = self.client.get(self.map_url, reference)
            self.assertFalse(page.context["filter_form"].errors)
            self.assertEqual(page.context["selection_counts"]["devices"], 1)
            self.assertEqual(parse_qs(urlsplit(page.context["save_filter_url"]).query), saved.parameters)
        applied = self.client.get(reverse("plugins:netbox_geoview:apply"), parameters)
        self.assertEqual(parse_qs(urlsplit(applied.url).query), saved.parameters)
        data = self.client.get(self.data_url, {"filter_id": saved.pk})
        self.assertEqual(data.status_code, 200)
        self.assertEqual(data.json()["config"]["site_markers"], page.context["map_config"]["site_markers"])
        request = RequestFactory().get("/")
        request.user = self.admin
        form = GeoViewMapWidget.ConfigForm({"saved_filter_id": saved.pk}, request=request)
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_status_or_operator_fails_closed(self):
        for parameters in ({"status": "missing"}, {"status": "active", "status_op": "bad"}):
            with self.subTest(parameters=parameters):
                page = self.client.get(self.map_url, parameters)
                self.assertTrue(page.context["filter_form"].errors)
                self.assertEqual(page.context["map_config"]["site_markers"], [])
                saved = self.post_filter(parameters)
                self.assertEqual(saved.status_code, 200)
                self.assertTrue(saved.context["form"].errors)
                choices = self.client.get(self.choices_url, {
                    "geoview_status": parameters["status"],
                    "geoview_status_op": parameters.get("status_op", "exact"),
                })
                self.assertEqual(choices.status_code, 400)
        self.assertFalse(SavedFilter.objects.exists())
        saved = SavedFilter.objects.create(
            name="Invalid status", slug="invalid-status", user=self.admin,
            parameters={"status": "missing"},
        )
        saved.object_types.add(ObjectType.objects.get_for_model(Device))
        self.assertEqual(self.client.get(self.data_url, {"filter_id": saved.pk}).status_code, 400)

    def test_status_results_respect_device_permissions(self):
        user = get_user_model().objects.create_user(username="status-reader")
        permission = ObjectPermission.objects.create(
            name="One offline device", actions=["view"], constraints={"pk": self.offline.pk}
        )
        permission.object_types.add(ObjectType.objects.get_for_model(Device))
        permission.users.add(user)
        self.client.force_login(user)
        page = self.client.get(self.map_url, {"status": ["active", "offline"]})
        self.assertEqual(page.context["selection_counts"]["devices"], 1)
        choices = self.client.get(self.choices_url, {"geoview_status": ["active", "offline"]})
        self.assertEqual(choices.status_code, 200)
        self.assertEqual([row["id"] for row in choices.json()["results"]], [self.offline.pk])
