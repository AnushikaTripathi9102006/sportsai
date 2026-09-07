from django.conf import settings
from django.db import models


class Appointment(models.Model):
    objects = models.Manager()

    STATUS_CHOICES = [
        ("CONFIRMED", "Confirmed"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
        ("MISSED", "Missed"),
    ]

    TIME_SLOT_CHOICES = [
        ("09:00 AM - 10:00 AM", "09:00 AM – 10:00 AM"),
        ("10:00 AM - 11:00 AM", "10:00 AM – 11:00 AM"),
        ("11:00 AM - 12:00 PM", "11:00 AM – 12:00 PM"),
        ("12:00 PM - 01:00 PM", "12:00 PM – 01:00 PM"),
        ("02:00 PM - 03:00 PM", "02:00 PM – 03:00 PM"),
        ("03:00 PM - 04:00 PM", "03:00 PM – 04:00 PM"),
    ]

    SLOT_CAPACITY = 5

    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointments",
    )

    produce = models.ForeignKey(
        "produce.Produce",
        on_delete=models.CASCADE,
        related_name="appointments",
    )

    procurement_record = models.ForeignKey(
        "procurement.ProcurementRecord",
        on_delete=models.CASCADE,
        related_name="appointments",
    )

    procurement_center = models.ForeignKey(
        "procurement.ProcurementCenter",
        on_delete=models.CASCADE,
        related_name="appointments",
    )

    appointment_date = models.DateField()

    appointment_time_slot = models.CharField(
        max_length=50,
        choices=TIME_SLOT_CHOICES,
        default="10:00 AM - 11:00 AM",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="CONFIRMED",
    )

    token_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-appointment_date", "appointment_time_slot"]

    def __str__(self):
        return f"APT-{self.id:04d} - {self.farmer.username} - {self.appointment_date} ({self.appointment_time_slot})"

    @property
    def appointment_code(self):
        return f"APT-{self.id:04d}"

    @property
    def formatted_slot_display(self):
        return f"{self.appointment_date.strftime('%d %b %Y')} ({self.appointment_time_slot})"

    def can_be_cancelled(self):
        if self.status != "CONFIRMED":
            return False
        if self.procurement_record and self.procurement_record.current_stage not in ["REGISTRATION", "APPOINTMENT"]:
            return False
        return True

