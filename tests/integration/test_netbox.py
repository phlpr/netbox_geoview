"""Run with NetBox's manage.py and tests/netbox_configuration.py.

Uses a separate PostgreSQL test database; upstream HTTP is mocked here.
"""
import json
from io import StringIO
from unittest.mock import Mock, patch

import requests
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from core.models import ObjectType
from dcim.models import Device, DeviceType, Location, Region, Site, SiteGroup
from extras.models import CustomField, SavedFilter, Tag
from tenancy.models import Tenant, TenantGroup
from users.models import ObjectPermission, Owner, OwnerGroup

from netbox_geoview.forms import GeoViewFilterForm, get_saved_filter_models
from netbox_geoview.management.commands.seed_geoview_testdata import Command
from netbox_geoview.views import GeoViewBaseView, GeoViewConfigMixin


class MapIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_geoview_testdata", stdout=StringIO())
        cls.admin = get_user_model().objects.create_superuser(
            username="geoview-test", password="test-only-password"
        )

    def setUp(self):
        self.client.force_login(self.admin)
        self.map_url = reverse("plugins:netbox_geoview:map")

    def get_map(self, params=None):
        response = self.client.get(self.map_url, params or {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["filter_form"].errors)
        return response

    def test_plugin_loaded_and_templates_render(self):
        self.assertTrue(apps.is_installed("netbox_geoview"))
        response = self.get_map()
        self.assertTemplateUsed(response, "netbox_geoview/map.html")
        self.assertContains(response, "netbox_geoview/geoview.js")
        self.assertEqual(response.context["map_config"]["site_markers"], [])

    def test_filter_tab(self):
        response = self.client.get(reverse("plugins:netbox_geoview:filter"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_tab"], "filter")

    def test_dynamic_choice_api_endpoints(self):
        # Exercise the real NetBox REST serializers used by the dropdown widgets.
        for endpoint in ("dcim/regions", "dcim/site-groups", "dcim/sites", "dcim/manufacturers",
                         "dcim/device-types", "dcim/platforms", "dcim/devices", "tenancy/tenant-groups",
                         "tenancy/tenants", "users/owner-groups", "users/owners", "extras/saved-filters"):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(f"/api/{endpoint}/", {"limit": 10}, HTTP_ACCEPT="application/json")
                self.assertEqual(response.status_code, 200)
                self.assertIn("results", response.json())

    def test_site_filters_and_popups(self):
        sites = Site.objects.filter(slug__startswith="geoview-")
        response = self.get_map({"site": list(sites.values_list("pk", flat=True))})
        markers = response.context["map_config"]["site_markers"]
        self.assertEqual(len(markers), 3)
        for marker in markers:
            self.assertEqual(marker["object_type"], "site")
            self.assertTrue(marker["popup_sections"])
        self.assertTrue(response.context["save_filter_url"])

    def test_device_search_coordinates_and_custom_fields(self):
        response = self.get_map({"q": "geoview"})
        markers = response.context["map_config"]["site_markers"]
        self.assertEqual(len(markers), 6)
        for device in Device.objects.all():
            marker = next(m for m in markers if m["name"] == device.name)
            source = device if device.latitude is not None else device.site
            self.assertEqual(marker["latitude"], float(source.latitude))
            self.assertEqual(marker["longitude"], float(source.longitude))
            fields = next(s for s in marker["popup_sections"] if s["title"] == "Custom Fields")
            self.assertIn("geoview_mapping", dict(fields["rows"]))

    def test_each_dynamic_filter(self):
        device = Device.objects.first()
        cases = {
            "region": device.site.region_id,
            "site_group": device.site.group_id,
            "site": device.site_id,
            "manufacturer": device.device_type.manufacturer_id,
            "device_type": device.device_type_id,
            "platform": device.platform_id,
            "device": device.pk,
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                response = self.get_map({field: value})
                self.assertTrue(response.context["map_config"]["site_markers"])

    def test_site_and_device_exclusion(self):
        site = Site.objects.first()
        response = self.get_map({"site": site.pk, "site_op": "n"})
        self.assertEqual(response.context["selection_counts"]["sites"], 2)
        self.assertNotIn(site.name, [m["name"] for m in response.context["map_config"]["site_markers"]])
        device = Device.objects.first()
        response = self.get_map({"device": device.pk, "device_op": "n"})
        self.assertEqual(response.context["selection_counts"]["devices"], 5)

    def test_tag_inclusion_exclusion_and_untagged(self):
        tag = Tag.objects.create(name="GeoView test", slug="geoview-test")
        Device.objects.first().tags.add(tag)
        for params, expected in [
            ({"tag": tag.slug}, 1),
            ({"tag": tag.slug, "tag_op": "n"}, 5),
            ({"tag": settings.FILTERS_NULL_CHOICE_VALUE}, 5),
        ]:
            with self.subTest(params=params):
                response = self.get_map(params)
                self.assertEqual(response.context["selection_counts"]["devices"], expected)

    def test_saved_filter_by_id_and_slug(self):
        saved = SavedFilter.objects.create(name="GeoView test", slug="geoview-test", parameters={"q": "geoview"})
        saved.object_types.add(ObjectType.objects.get_for_model(Device))
        for params in ({"filter_id": saved.pk}, {"filter": saved.slug}):
            with self.subTest(params=params):
                self.assertEqual(self.get_map(params).context["selection_counts"]["devices"], 6)

    def test_apply_preserves_query(self):
        response = self.client.get(reverse("plugins:netbox_geoview:apply"), {"q": "geoview"})
        self.assertRedirects(response, self.map_url + "?q=geoview")

    def test_invalid_filter_is_rendered_without_crash(self):
        response = self.client.get(self.map_url, {"site": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["filter_form"].errors)

    def test_invalid_saved_filter_id_is_rendered_without_crash(self):
        response = self.client.get(self.map_url, {"filter_id": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["filter_form"].errors)

    def test_tenant_and_owner_filters(self):
        tenant_group = TenantGroup.objects.create(name="Test tenants", slug="test-tenants")
        tenant = Tenant.objects.create(name="Test tenant", slug="test-tenant", group=tenant_group)
        owner_group = OwnerGroup.objects.create(name="Test owners")
        owner = Owner.objects.create(name="Test owner", group=owner_group)
        device = Device.objects.first()
        device.tenant = tenant
        device.owner = owner
        device.save()
        for field, obj in (("tenant", tenant), ("tenant_group", tenant_group), ("owner", owner), ("owner_group", owner_group)):
            for operator, expected in (("exact", 1), ("n", 5)):
                with self.subTest(field=field, operator=operator):
                    response = self.get_map({field: obj.pk, field + "_op": operator})
                    self.assertEqual(response.context["selection_counts"]["devices"], expected)

    def test_popup_data_is_safely_embedded(self):
        device = Device.objects.first()
        device.custom_field_data["geoview_service"] = "</script><script>alert('test')</script>"
        device.save()
        response = self.get_map({"device": device.pk})
        self.assertNotContains(response, "</script><script>alert('test')</script>")
        self.assertContains(response, r"\u003C/script\u003E")

    def test_tile_credentials_are_not_in_map_config(self):
        config = {"netbox_geoview": {"tile_layers": [{"name": "Private", "url": "https://tiles.example/{z}/{x}/{y}.png",
                    "headers": {"Authorization": "secret-value"}, "query": {"token": "secret-value"}}]}}
        with override_settings(PLUGINS_CONFIG=config):
            response = self.get_map()
            self.assertNotIn("secret-value", json.dumps(response.context["map_config"]))

    def test_unmappable_device_is_omitted_and_warned(self):
        device = Device.objects.first()
        Device.objects.filter(pk=device.pk).update(latitude=None, longitude=None)
        Site.objects.filter(pk=device.site_id).update(latitude=None, longitude=None)
        response = self.get_map({"device": device.pk})
        self.assertEqual(response.context["map_config"]["site_markers"], [])
        response = self.client.get(reverse("plugins:netbox_geoview:apply"), {"device": device.pk}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(list(response.context["messages"]))

    def test_zero_coordinates_are_preserved(self):
        device = Device.objects.first()
        device.latitude = device.longitude = 0
        self.assertEqual(GeoViewBaseView().get_device_coordinates(device), (0.0, 0.0))

    def test_custom_popup_mapping_and_values(self):
        config = {"netbox_geoview": {"popup_sections": {"device": [
            {"title": "Details", "mode": "table", "fields": [{"key": "name", "label": "Device"}]}
        ]}}}
        with override_settings(PLUGINS_CONFIG=config):
            response = self.get_map({"q": "geoview"})
            section = response.context["map_config"]["site_markers"][0]["popup_sections"][0]
            self.assertEqual(section["title"], "Details")
            self.assertEqual(section["rows"][0][0], "Device")
        values = GeoViewConfigMixin().normalize_custom_fields(Device.objects.first())
        self.assertIn(values["geoview_enabled"], ("true", "false"))
        self.assertIn("lab-cmdb", values["geoview_mapping"])

    def test_site_device_counts(self):
        for site in Site.objects.all():
            self.assertEqual(GeoViewConfigMixin().get_site_popup_values(site)["device_count"], 2)

    def test_seed_is_idempotent_and_hierarchy_survives(self):
        models = (Site, Location, DeviceType, Device, CustomField, Region, SiteGroup)
        before = {m: set(m.objects.values_list("pk", flat=True)) for m in models}
        call_command("seed_geoview_testdata", stdout=StringIO())
        for model in models:
            self.assertEqual(before[model], set(model.objects.values_list("pk", flat=True)))
        self.assertEqual(Location.objects.count(), 6)
        for location in Location.objects.exclude(parent=None):
            self.assertIn(location.parent, location.get_ancestors())
            self.assertEqual(location.site_id, location.parent.site_id)

    def test_seed_rolls_back_invalid_data(self):
        data = Command().load_data(None)
        data["region"]["name"] = "Should be rolled back"
        data["devices"][0]["device_type"] = "nonexistent"
        with patch.object(Command, "load_data", return_value=data):
            with self.assertRaises(KeyError):
                call_command("seed_geoview_testdata", stdout=StringIO())
        self.assertFalse(Region.objects.filter(name="Should be rolled back").exists())

    def test_saved_filter_model_selection(self):
        self.assertEqual(get_saved_filter_models({"site": [1]}), [Site])
        self.assertEqual(get_saved_filter_models({"q": "test"}), [Device])
        self.assertEqual(get_saved_filter_models(), [Site, Device])
        self.assertIn("filter_id", GeoViewFilterForm().fields)

    def test_anonymous_is_redirected_to_login(self):
        self.client.logout()
        for view in ("map", "filter", "apply", "route"):
            with self.subTest(view=view):
                response = self.client.get(reverse(f"plugins:netbox_geoview:{view}"))
                self.assertEqual(response.status_code, 302)
                self.assertIn("login", response.url)

    def test_user_without_object_permissions_sees_no_devices(self):
        user = get_user_model().objects.create_user(username="unprivileged")
        self.client.force_login(user)
        response = self.get_map({"q": "geoview"})
        self.assertEqual(response.context["map_config"]["site_markers"], [])

    def test_object_permissions_limit_devices(self):
        user = get_user_model().objects.create_user(username="restricted")
        device = Device.objects.first()
        permission = ObjectPermission.objects.create(name="One device", actions=["view"], constraints={"pk": device.pk})
        permission.object_types.add(ObjectType.objects.get_for_model(Device))
        permission.users.add(user)
        self.client.force_login(user)
        response = self.get_map({"q": "geoview"})
        self.assertEqual([m["name"] for m in response.context["map_config"]["site_markers"]], [device.name])

    def test_object_permissions_limit_sites_and_form_choices(self):
        user = get_user_model().objects.create_user(username="site-restricted")
        site = Site.objects.first()
        permission = ObjectPermission.objects.create(name="One site", actions=["view"], constraints={"pk": site.pk})
        permission.object_types.add(ObjectType.objects.get_for_model(Site))
        permission.users.add(user)
        self.client.force_login(user)
        response = self.get_map({"site": site.pk})
        self.assertEqual([m["name"] for m in response.context["map_config"]["site_markers"]], [site.name])
        response = self.client.get(self.map_url, {"site": Site.objects.exclude(pk=site.pk).first().pk})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["filter_form"].errors)
        self.assertEqual(response.context["map_config"]["site_markers"], [])

    def test_other_users_private_saved_filter_is_not_expanded(self):
        other = get_user_model().objects.create_user(username="private-filter-owner")
        saved = SavedFilter.objects.create(name="Private", slug="private", user=other, shared=False,
                                           parameters={"q": "DO-NOT-EXPOSE"})
        saved.object_types.add(ObjectType.objects.get_for_model(Device))
        for params in ({"filter_id": saved.pk}, {"filter": saved.slug}):
            response = self.client.get(self.map_url, params)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "DO-NOT-EXPOSE")

    def test_disabled_saved_filter_is_not_expanded(self):
        saved = SavedFilter.objects.create(name="Disabled", slug="disabled", enabled=False,
                                           parameters={"q": "DO-NOT-EXPAND"})
        response = self.client.get(self.map_url, {"filter": saved.slug})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "DO-NOT-EXPAND")


@override_settings(PLUGINS_CONFIG={"netbox_geoview": {"valhalla_url": "https://routing.example/route"}})
class ProxyIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(username="proxy-test", password="test-only-password")

    def setUp(self):
        self.client.force_login(self.admin)
        cache.clear()
        self.route_url = reverse("plugins:netbox_geoview:route")
        self.params = {"start_lat": 48.20849, "start_lon": 16.37208, "end_lat": 48.30694, "end_lon": 14.28583}
        self.tile_url = reverse("plugins:netbox_geoview:tile", kwargs={"layer_id": "openstreetmap", "z": 2, "x": 2, "y": 1})

    def test_route_profiles_and_alternatives(self):
        trip = {"summary": {"length": 207, "time": 8520}, "legs": [{"shape": "??AA"}]}
        for profile in ("auto", "bicycle", "pedestrian"):
            with self.subTest(profile=profile), patch("netbox_geoview.views.requests.post") as post:
                post.return_value = Mock(status_code=200)
                post.return_value.json.return_value = {"trip": trip, "alternates": [{"trip": trip}]}
                response = self.client.get(self.route_url, self.params | {"costing": profile})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["route"]["distance"], 207)
                self.assertEqual(response.json()["route"]["duration_minutes"], 142)
                self.assertEqual(len(response.json()["route"]["geometry"]), 2)
                self.assertEqual(len(response.json()["alternatives"]), 1)
                self.assertEqual(post.call_args.kwargs["json"]["costing"], profile)

    def test_route_invalid_and_missing_coordinates(self):
        for params in ({}, self.params | {"start_lat": 91}, self.params | {"end_lon": "invalid"}):
            with self.subTest(params=params), patch("netbox_geoview.views.requests.post") as post:
                self.assertEqual(self.client.get(self.route_url, params).status_code, 400)
                post.assert_not_called()

    def test_nonfinite_coordinates_are_rejected(self):
        for value in ("nan", "inf", "-inf"):
            with self.subTest(value=value), patch("netbox_geoview.views.requests.post") as post:
                self.assertEqual(self.client.get(self.route_url, self.params | {"start_lat": value}).status_code, 400)
                post.assert_not_called()

    def test_long_walking_route_rejected_before_upstream(self):
        params = self.params | {"end_lat": 51.5, "end_lon": -0.1, "costing": "pedestrian"}
        with patch("netbox_geoview.views.requests.post") as post:
            self.assertEqual(self.client.get(self.route_url, params).status_code, 400)
            post.assert_not_called()

    @override_settings(PLUGINS_CONFIG={"netbox_geoview": {}})
    def test_routing_disabled(self):
        self.assertEqual(self.client.get(self.route_url, self.params).status_code, 503)

    def test_upstream_timeout_and_connection_error(self):
        for exc in (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            with self.subTest(exc=exc), patch("netbox_geoview.views.requests.post", side_effect=exc):
                self.assertEqual(self.client.get(self.route_url, self.params).status_code, 502)

    def test_bad_upstream_json(self):
        with patch("netbox_geoview.views.requests.post") as post:
            post.return_value.json.side_effect = ValueError
            self.assertEqual(self.client.get(self.route_url, self.params).status_code, 502)

    def test_upstream_errors_and_no_route(self):
        for upstream_status, body, expected in ((400, {"error": "bad request"}, 400), (500, {}, 502), (200, {"trip": {}}, 404)):
            with self.subTest(status=upstream_status), patch("netbox_geoview.views.requests.post") as post:
                post.return_value = Mock(status_code=upstream_status)
                post.return_value.json.return_value = body
                self.assertEqual(self.client.get(self.route_url, self.params).status_code, expected)

    def test_tile_proxy_and_cache(self):
        with patch("netbox_geoview.views.requests.get") as get:
            get.return_value = Mock(status_code=200, content=b"image", headers={"Content-Type": "image/png"})
            for _ in range(2):
                response = self.client.get(self.tile_url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"image")
            get.assert_called_once()

    def test_unknown_tile_layer(self):
        self.assertEqual(self.client.get(self.tile_url.replace("openstreetmap", "unknown")).status_code, 404)

    def test_tile_upstream_failures(self):
        with patch("netbox_geoview.views.requests.get", side_effect=requests.exceptions.Timeout):
            self.assertEqual(self.client.get(self.tile_url).status_code, 502)
        with patch("netbox_geoview.views.requests.get") as get:
            get.return_value = Mock(status_code=200, content=b"error", headers={"Content-Type": "text/html"})
            self.assertEqual(self.client.get(self.tile_url).status_code, 502)
            get.return_value.status_code = 404
            self.assertEqual(self.client.get(self.tile_url).status_code, 404)
