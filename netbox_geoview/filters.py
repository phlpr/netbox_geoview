"""Resolve reusable GeoView filters without depending on a page or widget."""

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import QueryDict
from django.utils.translation import gettext_lazy as _

from dcim.models import Device, Site
from extras.models import SavedFilter
from core.models import ObjectType

SITE_FILTER_FIELDS = ("region", "site_group", "site")
DEVICE_FILTER_FIELDS = (
    "q",
    "tag",
    "manufacturer",
    "device_type",
    "platform",
    "role",
    "status",
    "tenant_group",
    "tenant",
    "owner_group",
    "owner",
    "device",
)
FIELD_OPERATOR_NAMES = tuple(
    field for field in SITE_FILTER_FIELDS + DEVICE_FILTER_FIELDS if field != "q"
)
SUPPORTED_LOOKUP_OPERATORS = {"exact", "n"}
FILTER_FIELDS = set(SITE_FILTER_FIELDS + DEVICE_FILTER_FIELDS)
FILTER_KEYS = FILTER_FIELDS | {f"{field}_op" for field in FIELD_OPERATOR_NAMES}
REFERENCE_KEYS = {"filter", "filter_id"}
LEGACY_DISPLAY_KEYS = {"lat", "lon", "zoom"}
ALIASES = {
    f"{field}_id": field
    for field in FIELD_OPERATOR_NAMES
    if field not in {"tag", "status"}
}
ALIASES["group_id"] = "site_group"


def _has_filter_value(source, field_name):
    if source is None:
        return False
    value = (
        source.getlist(field_name)
        if hasattr(source, "getlist")
        else source.get(field_name)
    )
    if hasattr(value, "exists"):
        return value.exists()
    if isinstance(value, (list, tuple, set)):
        return any(str(entry).strip() for entry in value if entry is not None)
    return value is not None and bool(str(value).strip())


def get_saved_filter_models(source=None):
    models = []
    if any(_has_filter_value(source, field) for field in SITE_FILTER_FIELDS):
        models.append(Site)
    if any(_has_filter_value(source, field) for field in DEVICE_FILTER_FIELDS):
        models.append(Device)
    return models or [Site, Device]


def get_usable_saved_filters(user):
    visible = Q(shared=True)
    if user.is_authenticated:
        visible |= Q(user=user)
    return SavedFilter.objects.restrict(user, "view").filter(visible, enabled=True)


def as_querydict(data):
    if hasattr(data, "getlist"):
        return data.copy()
    if not isinstance(data, dict):
        raise ValidationError(_("Filter parameters must be an object."))
    result = QueryDict(mutable=True)
    for key, value in data.items():
        values = value if isinstance(value, (list, tuple)) else [value]
        if any(isinstance(entry, (dict, list, tuple)) for entry in values):
            raise ValidationError(_("Filter values must be simple values or lists."))
        result.setlist(str(key), [str(entry) for entry in values if entry is not None])
    return result


def normalize_parameters(data, *, strict=False):
    result = QueryDict(mutable=True)
    for key, values in as_querydict(data).lists():
        field = ALIASES.get(key, key)
        if field in FILTER_KEYS or field in REFERENCE_KEYS:
            result.setlist(field, list(dict.fromkeys(values)))
        elif strict and key not in LEGACY_DISPLAY_KEYS:
            raise ValidationError(
                _("This filter contains unsupported conditions: %(field)s"),
                params={"field": key},
            )
    for field in FIELD_OPERATOR_NAMES:
        key = f"{field}_op"
        if key in result and (
            len(result.getlist(key)) != 1
            or result[key] not in SUPPORTED_LOOKUP_OPERATORS
        ):
            raise ValidationError(_("Unsupported filter operator."))
    return result


def resolve_filter_parameters(data, user, *, seen=()):
    """Expand accessible references; explicit URL values override saved values."""
    source = as_querydict(data or {})
    normalized = normalize_parameters(source)
    resolved = QueryDict(mutable=True)
    identifiers = [("pk", value) for value in normalized.getlist("filter_id") if value]
    identifiers += [("slug", value) for value in normalized.getlist("filter") if value]
    for lookup, value in identifiers:
        try:
            saved = get_usable_saved_filters(user).get(**{lookup: value})
        except (SavedFilter.DoesNotExist, ValueError, TypeError):
            raise ValidationError(_("The saved filter is unavailable.")) from None
        if saved.pk in seen or len(seen) >= 8:
            raise ValidationError(
                _("Saved filters contain a circular or excessively nested reference.")
            )
        parameters = normalize_parameters(saved.parameters, strict=True)
        compatible = [
            ObjectType.objects.get_for_model(model).pk for model in (Site, Device)
        ]
        if not saved.object_types.filter(pk__in=compatible).exists():
            raise ValidationError(
                _("This saved filter does not apply to sites or devices.")
            )
        expanded = resolve_filter_parameters(parameters, user, seen=(*seen, saved.pk))
        for field in FIELD_OPERATOR_NAMES:
            if expanded.getlist(field) and resolved.getlist(field):
                if expanded.get(f"{field}_op", "exact") != resolved.get(
                    f"{field}_op", "exact"
                ):
                    raise ValidationError(
                        _("The selected filters contain conflicting operators.")
                    )
        for key, values in expanded.lists():
            if key not in REFERENCE_KEYS:
                if (
                    key.endswith("_op")
                    and key in resolved
                    and resolved[key] != expanded[key]
                ):
                    raise ValidationError(
                        _("The selected filters contain conflicting operators.")
                    )
                resolved.setlist(
                    key, list(dict.fromkeys(resolved.getlist(key) + values))
                )
    for key, values in normalized.lists():
        resolved.setlist(key, values)
    return resolved


def filter_operators(parameters):
    return {
        field: parameters.get(f"{field}_op", "exact") for field in FIELD_OPERATOR_NAMES
    }


def serialize_parameters(parameters):
    """Persist effective conditions only, never references or display settings."""
    return {
        key: values
        for key, values in parameters.lists()
        if key in FILTER_KEYS
        and any(values)
        and (not key.endswith("_op") or any(parameters.getlist(key[:-3])))
    }
