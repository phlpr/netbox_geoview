from django.contrib.auth.mixins import AccessMixin


VIEW_PERMISSIONS = ("dcim.view_site", "dcim.view_device")


def can_view_geoview(user):
    """Require a login and either of NetBox's existing model view permissions."""
    return user.is_authenticated and user.is_active and any(
        user.has_perm(permission) for permission in VIEW_PERMISSIONS
    )


class GeoViewPermissionRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not can_view_geoview(request.user):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
