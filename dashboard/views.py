from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required
def dashboard(request):

    profile = request.user.profile

    if profile.role == "OFFICER" and not profile.is_approved:
        return redirect("pending_approval")

    return render(request, 'dashboard/dashboard.html')