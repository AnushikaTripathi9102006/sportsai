from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required
def dashboard(request):

    profile = request.user.profile

    # Officer approval check
    if profile.role == "OFFICER" and not profile.is_approved:
        return redirect("pending_approval")

    if profile.role == "FARMER":
        return redirect("farmer_dashboard")

    elif profile.role == "OFFICER":
        return redirect("officer_dashboard")

    elif profile.role == "ADMIN":
        return redirect("admin_dashboard")

    return redirect("login")


@login_required
def farmer_dashboard(request):

    profile = request.user.profile

    if profile.role != "FARMER":
        return redirect("dashboard")

    return render(
        request,
        "farmer/dashboard.html",
        {
            "farmer": request.user,
            "profile": profile,
        }
    )