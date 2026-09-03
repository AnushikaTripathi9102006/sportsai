from rest_framework.permissions import BasePermission


class ApprovedFarmerPermission(BasePermission):
    message = "Only approved farmers can use this feature."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        profile = getattr(request.user, "profile", None)
        return bool(
            profile
            and profile.role == "FARMER"
            and profile.is_approved
        )
