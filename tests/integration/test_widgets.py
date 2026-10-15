"""Saved filter round trips and real NetBox dashboard integration."""

import json
from io import StringIO
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from core.models import ObjectType
from dcim.models import Device, Site
from extras.models import SavedFilter
from netbox.registry import registry
from users.models import ObjectPermission

from netbox_geoview.widgets import GeoViewMapWidget


class SavedFilterWidgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_geoview_testdata", stdout=StringIO())
        cls.admin = get_user_model().objects.create_superuser(
            username="widget-admin", password="test-only"
        )
        cls.other = get_user_model().objects.create_user(username="widget-other")
        permission = ObjectPermission.objects.create(
            name="Widget reader", actions=["view"]
        )
        permission.object_types.set(
            ObjectType.objects.get_for_model(model)
            for model in (Device, Site, SavedFilter)
        )
        permission.users.add(cls.other)

    def setUp(self):
        self.client.force_login(self.admin)
        self.map_url = reverse("plugins:netbox_geoview:map")
        self.data_url = reverse("plugins:netbox_geoview:map_data")
        self.save_url = reverse("plugins:netbox_geoview:savedfilter_add")

    def saved(self, parameters, **kwargs):
        saved = SavedFilter.objects.create(
            name="Widget filter",
            slug="widget-filter",
            user=self.admin,
            parameters=parameters,
            **kwargs,
        )
        saved.object_types.set(
            ObjectType.objects.get_for_model(model) for model in (Site, Device)
        )
        return saved

    def post_filter(self, parameters, url=None, **kwargs):
        return self.client.post(
            url or self.save_url,
            {
                "name": "Saved via GeoView",
                "slug": "saved-via-geoview",
                "description": "Round trip",
                "parameters": json.dumps(parameters),
                **kwargs,
            },
        )

    def test_saved_exclusion_operators_match_full_map_and_widget(self):
        site = Site.objects.get(slug="geoview-vienna-dc")
        saved = self.saved({"site": [site.pk], "site_op": "n"})
        page = self.client.get(self.map_url, {"filter_id": saved.pk})
        data = self.client.get(self.data_url, {"filter_id": saved.pk})
        self.assertEqual(page.context["filter_ops"]["site"], "n")
        self.assertEqual(data.status_code, 200)
        self.assertEqual(
            data.json()["config"]["site_markers"],
            page.context["map_config"]["site_markers"],
        )
        self.assertEqual(len(data.json()["config"]["site_markers"]), 2)
        self.assertEqual(data["Cache-Control"], "private, no-store")

    def test_device_filters_are_constrained_by_selected_sites(self):
        site = Site.objects.get(slug="geoview-vienna-dc")
        page = self.client.get(self.map_url, {"site": site.pk, "q": "geoview"})
        self.assertEqual(
            page.context["selection_counts"]["devices"],
            Device.objects.filter(site=site).count(),
        )
        for marker in page.context["map_config"]["site_markers"]:
            if marker["object_type"] == "device":
                self.assertEqual(
                    Device.objects.get(name=marker["name"]).site_id, site.pk
                )

    def test_explicit_selections_override_saved_values(self):
        saved = self.saved({"q": "does-not-exist"})
        page = self.client.get(self.map_url, {"filter_id": saved.pk, "q": "geoview"})
        self.assertEqual(page.context["selection_counts"]["devices"], 6)

    def test_edited_conditions_do_not_reapply_cleared_saved_values(self):
        site = Site.objects.first()
        saved = self.saved({"site": [site.pk], "q": "geoview"})
        page = self.client.get(
            self.map_url,
            {"source_filter_id": saved.pk, "q": "geoview", "site_op": "exact"},
        )
        self.assertEqual(page.context["selection_counts"]["sites"], 0)
        self.assertEqual(page.context["selection_counts"]["devices"], 6)
        self.assertEqual(
            parse_qs(urlsplit(page.context["save_filter_url"]).query),
            {"q": ["geoview"]},
        )

    def test_combining_opposite_default_and_explicit_operators_is_rejected(self):
        site = Site.objects.first()
        first = self.saved({"site": [site.pk], "site_op": "n"})
        second = SavedFilter.objects.create(
            name="Other widget filter",
            slug="other-widget-filter",
            user=self.admin,
            parameters={"site": [site.pk]},
        )
        second.object_types.add(ObjectType.objects.get_for_model(Site))
        page = self.client.get(self.map_url, {"filter_id": [first.pk, second.pk]})
        self.assertTrue(page.context["filter_form"].errors)
        self.assertEqual(page.context["map_config"]["site_markers"], [])

    def test_widget_config_rejects_unsupported_saved_conditions(self):
        saved = self.saved({"cf_unknown": "x"})
        request = RequestFactory().get("/")
        request.user = self.admin
        form = GeoViewMapWidget.ConfigForm(
            {"saved_filter_id": saved.pk}, request=request
        )
        self.assertFalse(form.is_valid())
        self.assertIn("saved_filter_id", form.errors)
        saved.parameters = {"q": "geoview"}
        saved.save()
        saved.object_types.clear()
        self.assertFalse(
            GeoViewMapWidget.ConfigForm(
                {"saved_filter_id": saved.pk}, request=request
            ).is_valid()
        )

    def test_save_form_and_create_saved_filter(self):
        self.assertEqual(
            self.client.get(self.save_url, {"q": "geoview"}).status_code, 200
        )
        response = self.post_filter({"q": "geoview"})
        self.assertEqual(response.status_code, 302)
        saved = SavedFilter.objects.get(slug="saved-via-geoview")
        self.assertEqual(saved.user, self.admin)
        self.assertFalse(saved.shared)
        self.assertEqual(saved.parameters, {"q": ["geoview"]})
        self.assertEqual(
            list(saved.object_types.values_list("pk", flat=True)),
            [ObjectType.objects.get_for_model(Device).pk],
        )
        page = self.client.get(response.url)
        self.assertEqual(page.context["selection_counts"]["devices"], 6)
        self.assertTrue(page.context["update_filter_url"])

    def test_saving_flattens_references_and_omits_map_settings(self):
        saved = self.saved({"q": "geoview", "zoom": 12})
        response = self.post_filter(
            {"filter_id": saved.pk, "lat": 48, "lon": 16, "zoom": 9}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            SavedFilter.objects.get(slug="saved-via-geoview").parameters,
            {"q": ["geoview"]},
        )

    def test_update_saved_filter_and_copy_are_separate_operations(self):
        saved = self.saved({"q": "old"})
        edit = reverse("plugins:netbox_geoview:savedfilter_edit", args=[saved.pk])
        direct = self.client.get(edit)
        self.assertEqual(
            json.loads(direct.context["form"]["parameters"].value()), {"q": ["old"]}
        )
        self.assertEqual(self.client.get(edit, {"q": "geoview"}).status_code, 200)
        response = self.post_filter(
            {"q": "geoview"}, url=edit, name=saved.name, slug=saved.slug
        )
        self.assertEqual(response.status_code, 302)
        saved.refresh_from_db()
        self.assertEqual(saved.parameters, {"q": ["geoview"]})
        self.assertEqual(self.post_filter(saved.parameters).status_code, 302)
        self.assertEqual(SavedFilter.objects.filter(user=self.admin).count(), 2)

    def test_save_link_uses_effective_conditions_without_references(self):
        saved = self.saved({"q": "geoview"})
        response = self.client.get(self.map_url, {"filter_id": saved.pk, "zoom": 14})
        params = parse_qs(urlsplit(response.context["save_filter_url"]).query)
        self.assertEqual(params, {"q": ["geoview"]})

    def test_invalid_empty_or_unsupported_conditions_cannot_be_saved(self):
        for parameters in (
            {},
            {"cf_unknown": "x"},
            {"site": "not-an-id"},
            {"site_op": "bad"},
            {"q": {"nested": "x"}},
        ):
            with self.subTest(parameters=parameters):
                response = self.post_filter(parameters)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
        self.assertFalse(SavedFilter.objects.filter(user=self.admin).exists())

    def test_unsupported_deleted_disabled_or_circular_filters_fail_closed(self):
        saved = self.saved({"cf_unknown": "x"})
        cases = (
            {"cf_unknown": "x"},
            {"filter_id": saved.pk},
            {"q": "geoview", "q_op": "n"},
        )
        for parameters in cases:
            saved.parameters = parameters
            saved.save()
            with self.subTest(parameters=parameters):
                self.assertEqual(
                    self.client.get(self.data_url, {"filter_id": saved.pk}).status_code,
                    400,
                )
        saved.parameters = {"q": "geoview"}
        saved.enabled = False
        saved.save()
        self.assertEqual(
            self.client.get(self.data_url, {"filter_id": saved.pk}).status_code, 400
        )
        pk = saved.pk
        saved.delete()
        self.assertEqual(
            self.client.get(self.data_url, {"filter_id": pk}).status_code, 400
        )

    def test_empty_results_are_successful_and_do_not_show_other_objects(self):
        saved = self.saved({"q": "no-matching-device"})
        response = self.client.get(self.data_url, {"filter_id": saved.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["config"]["site_markers"], [])
        self.assertFalse(response.json()["config"]["ui"]["show_route_actions"])

    def test_widget_options_do_not_mutate_the_saved_filter(self):
        saved = self.saved({"q": "geoview"})
        response = self.client.get(
            self.data_url, {"filter_id": saved.pk, "fit_bounds": "0"}
        )
        self.assertFalse(response.json()["config"]["fit_bounds"])
        saved.refresh_from_db()
        self.assertEqual(saved.parameters, {"q": "geoview"})

    def test_shared_filters_are_rechecked_and_private_filters_are_not_available(self):
        saved = self.saved({"q": "geoview"}, shared=True)
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(self.data_url, {"filter_id": saved.pk}).status_code, 200
        )
        saved.shared = False
        saved.save()
        self.assertEqual(
            self.client.get(self.data_url, {"filter_id": saved.pk}).status_code, 400
        )

        self.client.get("/")
        dashboard = self.other.dashboard
        widget = GeoViewMapWidget(config={"saved_filter_id": saved.pk})
        dashboard.add_widget(widget)
        dashboard.save()
        dialog = self.client.get(
            reverse("extras:dashboardwidget_config", kwargs={"id": widget.id}),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(dialog.status_code, 200)
        self.assertNotContains(dialog, saved.name)
        denied = self.client.post(
            reverse("extras:dashboardwidget_add"),
            {
                "widget_class": "netbox_geoview.GeoViewMapWidget",
                "config-saved_filter_id": saved.pk,
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertNotIn("HX-Redirect", denied.headers)

    def test_shared_filter_never_grants_object_permissions(self):
        saved = self.saved({"q": "geoview"}, shared=True)
        user = get_user_model().objects.create_user(username="widget-constrained")
        device = Device.objects.first()
        permission = ObjectPermission.objects.create(
            name="One widget device", actions=["view"], constraints={"pk": device.pk}
        )
        permission.object_types.add(ObjectType.objects.get_for_model(Device))
        permission.users.add(user)
        filters = ObjectPermission.objects.create(
            name="Read widget filter", actions=["view"]
        )
        filters.object_types.add(ObjectType.objects.get_for_model(SavedFilter))
        filters.users.add(user)
        self.client.force_login(user)
        response = self.client.get(self.data_url, {"filter_id": saved.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [marker["name"] for marker in response.json()["config"]["site_markers"]],
            [device.name],
        )

    def test_create_update_and_data_endpoints_enforce_permissions(self):
        saved = self.saved({"q": "geoview"}, shared=True)
        edit = reverse("plugins:netbox_geoview:savedfilter_edit", args=[saved.pk])
        self.client.logout()
        for url in (self.data_url, self.save_url, edit):
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.post_filter({"q": "geoview"}).status_code, 403)
        self.assertEqual(self.post_filter({"q": "x"}, url=edit).status_code, 403)
        permission = ObjectPermission.objects.create(
            name="Change filters", actions=["change"]
        )
        permission.object_types.add(ObjectType.objects.get_for_model(SavedFilter))
        permission.users.add(self.other)
        self.assertEqual(self.client.get(edit).status_code, 403)

    def test_save_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(
            client.post(self.save_url, {"parameters": "{}"}).status_code, 403
        )

    def test_widget_is_registered_and_real_dashboard_config_is_json_serializable(self):
        self.assertIs(
            registry["widgets"]["netbox_geoview.GeoViewMapWidget"], GeoViewMapWidget
        )
        saved = self.saved({"q": "geoview"})
        self.client.get("/")
        response = self.client.post(
            reverse("extras:dashboardwidget_add"),
            {
                "widget_class": "netbox_geoview.GeoViewMapWidget",
                "title": "Widget test",
                "config-saved_filter_id": saved.pk,
                "config-fit_bounds": "on",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("HX-Redirect", response.headers)
        self.admin.refresh_from_db()
        config = next(
            value
            for value in self.admin.dashboard.config.values()
            if value["class"] == "netbox_geoview.GeoViewMapWidget"
        )
        self.assertEqual(
            config["config"], {"saved_filter_id": saved.pk, "fit_bounds": True}
        )
        self.assertContains(self.client.get("/"), "data-geoview-widget=")

    def test_two_widgets_render_independent_ids_and_settings(self):
        request = RequestFactory().get("/")
        request.user = self.admin
        first = GeoViewMapWidget(id="first", config={"saved_filter_id": 1}).render(
            request
        )
        second = GeoViewMapWidget(
            id="second", config={"saved_filter_id": 2, "fit_bounds": False}
        ).render(request)
        self.assertIn('data-geoview-widget="first"', first)
        self.assertIn('data-geoview-widget="second"', second)
        self.assertIn("filter_id=1", first)
        self.assertIn("fit_bounds=0", second)
