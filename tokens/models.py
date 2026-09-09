import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Token(models.Model):
    objects = models.Manager()

    STATUS_CHOICES = [
        ("WAITING", "Waiting in Queue"),
        ("CALLED", "Called - Your Turn"),
        ("IN_PROGRESS", "In Inspection / Processing"),
        ("COMPLETED", "Procurement Completed"),
        ("MISSED", "Missed"),
        ("CANCELLED", "Cancelled"),
    ]

    token_number = models.CharField(max_length=50)
    sequence_number = models.IntegerField()

    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tokens",
    )

    produce = models.ForeignKey(
        "produce.Produce",
        on_delete=models.CASCADE,
        related_name="tokens",
    )

    procurement_record = models.ForeignKey(
        "procurement.ProcurementRecord",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tokens",
    )

    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tokens",
    )

    procurement_center = models.ForeignKey(
        "procurement.ProcurementCenter",
        on_delete=models.CASCADE,
        related_name="tokens",
    )

    date = models.DateField(default=timezone.now)
    counter_number = models.CharField(max_length=20, default="Counter 1")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="WAITING",
    )

    secure_qr_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    issued_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "sequence_number"]
        unique_together = ["procurement_center", "date", "sequence_number"]

    def __str__(self):
        return f"{self.token_number} - {self.farmer.username} ({self.get_status_display()})"

    def get_queue_position(self):
        if self.status not in ["WAITING", "CALLED"]:
            return 0

        tokens_ahead = Token.objects.filter(
            procurement_center=self.procurement_center,
            date=self.date,
            status__in=["WAITING", "CALLED"],
            sequence_number__lt=self.sequence_number,
        ).count()

        return tokens_ahead + 1

    def get_farmers_ahead(self):
        pos = self.get_queue_position()
        return max(0, pos - 1)

    def get_estimated_wait_display(self):
        if self.status == "CALLED":
            return "Immediate (Your Turn)"
        if self.status == "IN_PROGRESS":
            return "In Counter Processing"
        if self.status == "COMPLETED":
            return "Completed"
        if self.status in ["CANCELLED", "MISSED"]:
            return "N/A"

        ahead = self.get_farmers_ahead()
        if ahead == 0:
            return "~5 minutes"
        mins = ahead * 10
        return f"~{mins} minutes"

    def is_your_turn(self):
        return self.status == "CALLED"

