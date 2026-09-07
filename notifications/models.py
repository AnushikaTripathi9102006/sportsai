from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("GENERAL", "General Notification"),
        ("PRODUCE", "Produce Registration / Update"),
        ("PROCUREMENT", "Procurement Request / Status"),
        ("APPOINTMENT", "Appointment Schedule"),
        ("TOKEN", "Token & Live Queue"),
        ("QUALITY", "Quality Inspection"),
        ("WEIGHING", "Scale Weighing"),
        ("BILL", "Procurement Bill"),
        ("PAYMENT", "Payment & Payout"),
        ("SYSTEM", "System Alert / Approval"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default="GENERAL",
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    target_url = models.CharField(max_length=255, blank=True, default="")

    related_object_type = models.CharField(max_length=50, blank=True, default="")
    related_object_id = models.PositiveIntegerField(null=True, blank=True)

    event_key = models.CharField(max_length=100, blank=True, default="", db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.get_notification_type_display()})"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
