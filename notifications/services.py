from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from .models import Notification

User = get_user_model()


def create_notification(
    user,
    title,
    message,
    notification_type="GENERAL",
    target_url="",
    related_object=None,
    event_key=None,
):
    """
    Centralized notification creator with idempotency protection.
    If `event_key` is provided and a notification already exists for this user with that key,
    it returns the existing notification without creating a duplicate.
    """
    if not user or not user.is_authenticated:
        return None

    if event_key:
        existing = Notification.objects.filter(user=user, event_key=event_key).first()
        if existing:
            return existing

    rel_type = ""
    rel_id = None
    if related_object:
        rel_type = related_object.__class__.__name__
        rel_id = getattr(related_object, "pk", getattr(related_object, "id", None))

    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url,
        related_object_type=rel_type,
        related_object_id=rel_id,
        event_key=event_key or "",
    )


def notify_farmer(
    farmer_user,
    title,
    message,
    notification_type="GENERAL",
    target_url="",
    related_object=None,
    event_key=None,
):
    return create_notification(
        user=farmer_user,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url,
        related_object=related_object,
        event_key=event_key,
    )


def notify_officer(
    officer_user,
    title,
    message,
    notification_type="GENERAL",
    target_url="",
    related_object=None,
    event_key=None,
):
    return create_notification(
        user=officer_user,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url,
        related_object=related_object,
        event_key=event_key,
    )


def notify_admin(
    title,
    message,
    notification_type="SYSTEM",
    target_url="",
    related_object=None,
    event_key=None,
):
    admins = User.objects.filter(
        models.Q(is_superuser=True) | models.Q(is_staff=True) | models.Q(profile__role="ADMIN")
    ).distinct()

    created_list = []
    for admin_user in admins:
        notif = create_notification(
            user=admin_user,
            title=title,
            message=message,
            notification_type=notification_type,
            target_url=target_url,
            related_object=related_object,
            event_key=f"{event_key}_admin_{admin_user.id}" if event_key else None,
        )
        if notif:
            created_list.append(notif)
    return created_list
