from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Notification


@login_required
def notifications(request):
    profile = getattr(request.user, "profile", None)

    # Fetch user notifications
    user_notifications = Notification.objects.filter(user=request.user).order_by("-created_at")

    selected_category = request.GET.get("category", "all").lower()
    selected_tab = request.GET.get("tab", "all").lower()

    filtered = user_notifications

    if selected_category != "all":
        cat_map = {
            "token": "TOKEN",
            "appointment": "APPOINTMENT",
            "procurement": "PROCUREMENT",
            "payment": "PAYMENT",
            "produce": "PRODUCE",
            "quality": "QUALITY",
            "weighing": "WEIGHING",
            "bill": "BILL",
            "system": "SYSTEM",
        }
        if selected_category in cat_map:
            filtered = filtered.filter(notification_type=cat_map[selected_category])

    if selected_tab == "unread":
        filtered = filtered.filter(is_read=False)

    unread_count = user_notifications.filter(is_read=False).count()
    all_count = user_notifications.count()

    action_required_types = ["TOKEN", "APPOINTMENT", "SYSTEM"]
    action_count = user_notifications.filter(notification_type__in=action_required_types, is_read=False).count()
    smart_count = user_notifications.filter(notification_type__in=["PRODUCE", "PROCUREMENT", "PAYMENT"]).count()

    return render(
        request,
        "notifications/notifications.html",
        {
            "farmer": request.user,
            "profile": profile,
            "notifications_list": filtered,
            "unread_count": unread_count,
            "all_count": all_count,
            "action_count": action_count,
            "smart_count": smart_count,
            "selected_category": selected_category,
            "selected_tab": selected_tab,
        },
    )


@login_required
def mark_as_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.mark_as_read()

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
        return JsonResponse({"status": "success", "id": pk, "is_read": True})

    messages.success(request, f"Notification '{notif.title}' marked as read.")
    if notif.target_url:
        return redirect(notif.target_url)
    return redirect("notifications:notifications")


@login_required
def mark_all_as_read(request):
    updated = Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now(),
    )

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
        return JsonResponse({"status": "success", "updated_count": updated})

    messages.success(request, f"All {updated} unread notification(s) marked as read.")
    return redirect("notifications:notifications")


@login_required
def unread_count_api(request):
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"unread_count": unread_count})
