"""Exercise menu rendering and every endpoint with real NetBox permissions."""
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import ObjectType
from dcim.models import Device, Region, Site
from users.models import Group, ObjectPermission


@override_settings(
    LOGIN_REQUIRED=False,
    DEFAULT_PERMISSIONS={},
    EXEMPT_VIEW_PERMISSIONS=[],
    PLUGINS_CONFIG={"netbox_geoview": {"valhalla_url": "https://routing.example/route"}},
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class GeoViewAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for name, models, actions, enabled in (
            ("none", (), ("view",), True),
            ("unrelated", (Region,), ("view",), True),
            ("change-only", (Site, Device), ("change",), True),
            ("disabled", (Site, Device), ("view",), False),
            ("site", (Site,), ("view",), True),
            ("device", (Device,), ("view",), True),
            ("both", (Site, Device), ("view",), True),
            ("group", (Device,), ("view",), True),
        ):
            user = get_user_model().objects.create_user(username=f"access-{name}")
            cls.users[name] = user
            if models:
                permission = ObjectPermission.objects.create(
                    name=name, actions=list(actions), enabled=enabled,
                    # Model access must work even when constraints match no objects.
                    constraints={"pk": -1},
                )
                permission.object_types.set(ObjectType.objects.get_for_model(m) for m in models)
                if name == "group":
                    group = Group.objects.create(name="GeoView readers")
                    permission.groups.add(group)
                    user.groups.add(group)
                else:
                    permission.users.add(user)
        cls.users["admin"] = get_user_model().objects.create_superuser(username="access-admin")

    def setUp(self):
        cache.clear()
        self.urls = {
            name: reverse(f"plugins:netbox_geoview:{name}")
            for name in ("map", "filter", "apply", "route")
        }
        self.urls["tile"] = reverse(
            "plugins:netbox_geoview:tile",
            kwargs={"layer_id": "openstreetmap", "z": 2, "x": 2, "y": 1},
        )
        self.route_params = {"start_lat": 48, "start_lon": 16, "end_lat": 48.1, "end_lon": 16.1}

    def assert_menu(self, visible):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        link = f'href="{self.urls["map"]}"'
        if visible:
            self.assertContains(response, link, count=1)
        else:
            self.assertNotContains(response, link)
            self.assertNotContains(response, 'mdi-map-marker-radius-outline')

    def assert_denied(self, status):
        with patch("netbox_geoview.views.requests.get") as get, \
                patch("netbox_geoview.views.requests.post") as post:
            for name, url in self.urls.items():
                with self.subTest(endpoint=name):
                    response = self.client.get(url, self.route_params if name == "route" else {})
                    self.assertEqual(response.status_code, status)
                    if status == 302:
                        target = urlsplit(response.url)
                        self.assertEqual(target.path, reverse("login"))
                        self.assertTrue(parse_qs(target.query)["next"][0].startswith(url))
            get.assert_not_called()
            post.assert_not_called()

    def assert_allowed(self):
        with patch("netbox_geoview.views.requests.get") as get, \
                patch("netbox_geoview.views.requests.post") as post:
            get.return_value = Mock(status_code=200, content=b"tile", headers={"Content-Type": "image/png"})
            post.return_value = Mock(status_code=200)
            post.return_value.json.return_value = {
                "trip": {"summary": {"length": 1, "time": 60}, "legs": [{"shape": "??AA"}]},
            }
            for name, url in self.urls.items():
                with self.subTest(endpoint=name):
                    response = self.client.get(url, self.route_params if name == "route" else {})
                    self.assertEqual(response.status_code, 302 if name == "apply" else 200)
                    if name == "apply":
                        self.assertEqual(response.url, self.urls["map"])
                    elif name == "tile":
                        self.assertEqual(response.content, b"tile")
                        self.assertEqual(response["Cache-Control"], "private, no-cache")

    def test_anonymous_hidden_and_denied_even_with_public_netbox(self):
        for exemptions in ([], ["*"]):
            with self.subTest(exemptions=exemptions), override_settings(EXEMPT_VIEW_PERMISSIONS=exemptions):
                self.assert_menu(False)
                self.assert_denied(302)
        with override_settings(LOGIN_REQUIRED=True):
            self.assert_denied(302)

    def test_users_without_either_view_permission_are_hidden_and_denied(self):
        for name in ("none", "unrelated", "change-only", "disabled"):
            with self.subTest(user=name):
                self.client.force_login(self.users[name])
                self.assert_menu(False)
                for login_required in (False, True):
                    with override_settings(LOGIN_REQUIRED=login_required):
                        self.assert_denied(403)

    def test_either_model_group_and_superuser_permissions_grant_access(self):
        for name in ("site", "device", "both", "group", "admin"):
            with self.subTest(user=name):
                self.client.force_login(self.users[name])
                self.assert_menu(True)
                self.assert_allowed()

    def test_netbox_default_and_exempt_permissions_still_apply_after_login(self):
        self.client.force_login(self.users["none"])
        for config in (
            {"DEFAULT_PERMISSIONS": {"dcim.view_site": ({"pk": -1},)}},
            {"EXEMPT_VIEW_PERMISSIONS": ["dcim.device"]},
        ):
            with self.subTest(config=config), override_settings(**config):
                self.assert_menu(True)
                self.assert_allowed()

    def test_menu_access_is_not_cached_between_users(self):
        for name, visible in (("admin", True), ("none", False), ("device", True), (None, False), ("site", True)):
            with self.subTest(user=name):
                if name is None:
                    self.client.logout()
                else:
                    self.client.force_login(self.users[name])
                self.assert_menu(visible)

    def test_revoking_permissions_blocks_endpoints_including_cached_tiles(self):
        self.client.force_login(self.users["group"])
        self.assert_allowed()
        self.users["group"].groups.clear()
        self.assert_menu(False)
        self.assert_denied(403)
        self.client.logout()
        self.assert_denied(302)
