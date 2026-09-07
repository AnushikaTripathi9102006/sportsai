from .models import Notification


def unread_notifications(request):
    """
    Injects unread notification counts and latest notifications
    into template context for authenticated users.
    """
    if hasattr(request, "user") and request.user.is_authenticated:
        qs = Notification.objects.filter(user=request.user)
        unread_count = qs.filter(is_read=False).count()
        latest = qs[:5]
        return {
            "unread_notifications_count": unread_count,
            "topbar_notifications": latest,
        }
    return {
        "unread_notifications_count": 0,
        "topbar_notifications": [],
    }
