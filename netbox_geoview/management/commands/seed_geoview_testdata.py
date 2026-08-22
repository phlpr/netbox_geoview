import json
from decimal import Decimal
from importlib import resources
from pathlib import Path

from core.models import ObjectType
from dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Location,
    Manufacturer,
    Platform,
    Region,
    Site,
    SiteGroup,
)
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from extras.choices import CustomFieldTypeChoices
from extras.models import CustomField


CUSTOM_FIELD_TYPES = {
    "boolean": CustomFieldTypeChoices.TYPE_BOOLEAN,
    "json": CustomFieldTypeChoices.TYPE_JSON,
    "text": CustomFieldTypeChoices.TYPE_TEXT,
}


class Command(BaseCommand):
    help = "Create or refresh the reusable GeoView development data set."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-file",
            type=Path,
            help="Optional path to an alternative GeoView seed-data JSON file.",
        )

    def handle(self, *args, **options):
        data = self.load_data(options.get("data_file"))
        with transaction.atomic():
            summary = self.seed(data)

        self.stdout.write(self.style.SUCCESS("GeoView test data is ready."))
        for model_name, count in summary.items():
            self.stdout.write(f"  {model_name}: {count}")

    def load_data(self, data_file):
        try:
            if data_file:
                return json.loads(data_file.read_text(encoding="utf-8"))
            resource = resources.files("netbox_geoview.testdata").joinpath(
                "geoview_seed_data.json"
            )
            return json.loads(resource.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Unable to load GeoView seed data: {exc}") from exc

    def seed(self, data):
        region, _ = Region.objects.update_or_create(
            slug=data["region"]["slug"],
            defaults={
                "name": data["region"]["name"],
                "description": data["region"].get("description", ""),
            },
        )
        site_group, _ = SiteGroup.objects.update_or_create(
            slug=data["site_group"]["slug"],
            defaults={
                "name": data["site_group"]["name"],
                "description": data["site_group"].get("description", ""),
            },
        )
        manufacturer, _ = Manufacturer.objects.update_or_create(
            slug=data["manufacturer"]["slug"],
            defaults={
                "name": data["manufacturer"]["name"],
                "description": data["manufacturer"].get("description", ""),
            },
        )
        platform, _ = Platform.objects.update_or_create(
            manufacturer=manufacturer,
            slug=data["platform"]["slug"],
            defaults={
                "name": data["platform"]["name"],
                "description": data["platform"].get("description", ""),
            },
        )

        self.seed_custom_fields(data["custom_fields"])

        sites = {}
        for spec in data["sites"]:
            site, _ = Site.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "name": spec["name"],
                    "status": "active",
                    "region": region,
                    "group": site_group,
                    "facility": spec.get("facility", ""),
                    "physical_address": spec.get("physical_address", ""),
                    "latitude": self.decimal_or_none(spec.get("latitude")),
                    "longitude": self.decimal_or_none(spec.get("longitude")),
                    "description": spec.get("description", ""),
                    "custom_field_data": spec.get("custom_fields", {}),
                },
            )
            site.full_clean()
            site.save()
            sites[spec["key"]] = site

        locations = {}
        for spec in data["locations"]:
            parent = locations.get(spec.get("parent"))
            location, _ = Location.objects.update_or_create(
                site=sites[spec["site"]],
                parent=parent,
                slug=spec["slug"],
                defaults={
                    "name": spec["name"],
                    "status": "active",
                    "facility": spec.get("facility", ""),
                    "description": "GeoView reusable test location",
                },
            )
            location.full_clean()
            location.save()
            locations[spec["key"]] = location

        roles = {}
        for spec in data["roles"]:
            role, _ = DeviceRole.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "name": spec["name"],
                    "color": spec["color"],
                    "vm_role": False,
                    "description": "GeoView reusable test role",
                },
            )
            roles[spec["key"]] = role

        device_types = {}
        for spec in data["device_types"]:
            device_type, _ = DeviceType.objects.update_or_create(
                manufacturer=manufacturer,
                slug=spec["slug"],
                defaults={
                    "model": spec["model"],
                    "part_number": spec.get("part_number", ""),
                    "u_height": Decimal(spec.get("u_height", "1.0")),
                    "is_full_depth": spec.get("is_full_depth", True),
                    "default_platform": platform,
                    "description": "GeoView reusable test device type",
                },
            )
            device_type.full_clean()
            device_type.save()
            device_types[spec["key"]] = device_type

        devices = []
        for spec in data["devices"]:
            site = sites[spec["site"]]
            device, _ = Device.objects.update_or_create(
                name=spec["name"],
                site=site,
                defaults={
                    "location": locations[spec["location"]],
                    "device_type": device_types[spec["device_type"]],
                    "role": roles[spec["role"]],
                    "platform": platform,
                    "status": "active",
                    "serial": spec.get("serial", ""),
                    "asset_tag": spec.get("asset_tag"),
                    "latitude": self.decimal_or_none(spec.get("latitude")),
                    "longitude": self.decimal_or_none(spec.get("longitude")),
                    "description": "GeoView reusable test device",
                    "custom_field_data": spec.get("custom_fields", {}),
                },
            )
            device.full_clean()
            device.save()
            devices.append(device)

        return {
            "regions": 1,
            "site groups": 1,
            "sites": len(sites),
            "locations": len(locations),
            "manufacturers": 1,
            "platforms": 1,
            "device roles": len(roles),
            "device types": len(device_types),
            "devices": len(devices),
            "custom fields": len(data["custom_fields"]),
        }

    def seed_custom_fields(self, specs):
        object_types = [
            ObjectType.objects.get_for_model(Site),
            ObjectType.objects.get_for_model(Device),
        ]
        for spec in specs:
            try:
                field_type = CUSTOM_FIELD_TYPES[spec["type"]]
            except KeyError as exc:
                raise CommandError(
                    f"Unsupported custom field type: {spec['type']}"
                ) from exc
            custom_field, _ = CustomField.objects.update_or_create(
                name=spec["name"],
                defaults={
                    "label": spec.get("label", ""),
                    "type": field_type,
                    "group_name": "GeoView Test Data",
                    "description": spec.get("description", ""),
                    "required": False,
                },
            )
            custom_field.object_types.set(object_types)

    @staticmethod
    def decimal_or_none(value):
        return Decimal(value) if value is not None else None
