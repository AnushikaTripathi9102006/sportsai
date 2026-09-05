from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from procurement.models import ProcurementCenter


def officer_required(view_func):
    """
    Decorator to restrict access to approved Procurement Officers only.
    Redirects unapproved officers to pending_approval and non-officers to dashboard.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        profile = getattr(request.user, "profile", None)
        if not profile:
            messages.error(request, "User profile not found.")
            return redirect("dashboard")

        if profile.role != "OFFICER":
            messages.error(request, "Unauthorized access. Procurement Officer role required.")
            return redirect("dashboard")

        if not profile.is_approved:
            return redirect("pending_approval")

        # Auto-assign first active center if none assigned yet
        if not profile.assigned_center:
            center = ProcurementCenter.objects.filter(is_active=True).first()
            if center:
                profile.assigned_center = center
                profile.save()

        return view_func(request, *args, **kwargs)

    return _wrapped_view
