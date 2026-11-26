"""Exercise GeoView against NetBox's real read-only database sessions."""

import json
from io import StringIO
from unittest import skipIf

from packaging.version import Version
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from core.models import ObjectType
from dcim.models import Device
from extras.models import Dashboard, SavedFilter

from netbox_geoview.widgets import GeoViewMapWidget


@skipIf(
    Version(settings.VERSION) < Version("4.7.6"),
    "Read-only request enforcement requires NetBox 4.7.6 (#23552)",
)
class MaintenanceModeTests(TransactionTestCase):
    # TestCase's wrapping transaction would bypass SET SESSION READ ONLY.
    def setUp(self):
        call_command("seed_geoview_testdata", stdout=StringIO())
        self.user = get_user_model().objects.create_superuser(
            username="maintenance-admin", password="test-only"
        )
        self.client.force_login(self.user)
        self.saved = SavedFilter.objects.create(
            name="Read-only map", slug="read-only-map", user=self.user,
            parameters={"q": ["geoview"]},
        )
        self.saved.object_types.add(ObjectType.objects.get_for_model(Device))
        self.dashboard = Dashboard.objects.create(user=self.user, config={})
        self.dashboard.add_widget(
            GeoViewMapWidget(config={"saved_filter_id": self.saved.pk})
        )
        self.dashboard.save()
        self.add_url = reverse("plugins:netbox_geoview:savedfilter_add")
        self.edit_url = reverse(
            "plugins:netbox_geoview:savedfilter_edit", args=[self.saved.pk]
        )

    def tearDown(self):
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE")

    def assert_writable_connection(self):
        with connection.cursor() as cursor:
            cursor.execute("SHOW transaction_read_only")
            self.assertEqual(cursor.fetchone()[0], "off")

    def test_maps_choices_saved_filters_and_dashboard_remain_readable(self):
        with override_settings(MAINTENANCE_MODE=True):
            page = self.client.get(
                reverse("plugins:netbox_geoview:map"), {"filter_id": self.saved.pk}
            )
            self.assertEqual(page.status_code, 200)
            self.assertEqual(page.context["selection_counts"]["devices"], 6)
            data = self.client.get(
                reverse("plugins:netbox_geoview:map_data"), {"filter_id": self.saved.pk}
            )
            self.assertEqual(data.status_code, 200)
            self.assertEqual(len(data.json()["config"]["site_markers"]), 6)
            choices = self.client.get(
                reverse("plugins:netbox_geoview:device_choices"), {"q": "geoview"}
            )
            self.assertEqual(choices.status_code, 200)
            self.assertEqual(choices.json()["count"], 6)
            self.assertContains(self.client.get("/"), "data-geoview-widget=")
            self.assertEqual(self.client.get(self.edit_url).status_code, 200)
        self.assert_writable_connection()
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.parameters, {"q": ["geoview"]})

    def test_filter_writes_are_refused_and_resume_after_maintenance(self):
        payload = {
            "name": "Blocked filter", "slug": "blocked-filter",
            "parameters": json.dumps({"q": ["gv-vie-core-01"]}),
        }
        with override_settings(MAINTENANCE_MODE=True):
            for url in (self.add_url, self.edit_url):
                with self.subTest(url=url):
                    response = self.client.post(url, payload)
                    self.assertRedirects(response, url, fetch_redirect_response=False)
                    self.assertIn(
                        "maintenance mode",
                        " ".join(str(message) for message in get_messages(response.wsgi_request)),
                    )
                    self.assert_writable_connection()
            self.assertFalse(SavedFilter.objects.filter(slug="blocked-filter").exists())
            self.saved.refresh_from_db()
            self.assertEqual(self.saved.parameters, {"q": ["geoview"]})
            self.assertEqual(self.saved.slug, "read-only-map")
        response = self.client.post(self.add_url, payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            SavedFilter.objects.get(slug="blocked-filter").parameters,
            {"q": ["gv-vie-core-01"]},
        )

    def test_dashboard_writes_are_refused_and_default_dashboard_is_not_saved(self):
        original = self.dashboard.config.copy()
        url = reverse("extras:dashboardwidget_add")
        with override_settings(MAINTENANCE_MODE=True):
            response = self.client.post(
                url,
                {"widget_class": "netbox_geoview.GeoViewMapWidget",
                 "title": "Blocked widget", "config-saved_filter_id": self.saved.pk},
                HTTP_HX_REQUEST="true",
            )
            self.assertRedirects(response, url, fetch_redirect_response=False)
            self.dashboard.refresh_from_db()
            self.assertEqual(self.dashboard.config, original)
        self.assert_writable_connection()
        self.dashboard.delete()
        with override_settings(MAINTENANCE_MODE=True):
            self.assertEqual(self.client.get("/").status_code, 200)
            self.assertFalse(Dashboard.objects.filter(user=self.user).exists())
