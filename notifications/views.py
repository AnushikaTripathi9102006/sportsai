from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def notifications(request):
    profile = getattr(request.user, "profile", None)

    return render(
        request,
        "notifications/notifications.html",
        {
            "farmer": request.user,
            "profile": profile,
        },
    )
