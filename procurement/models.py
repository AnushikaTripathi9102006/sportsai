from django.conf import settings
from django.db import models


class ProcurementRecord(models.Model):
    STAGE_CHOICES = [
        ("REGISTERED", "Produce Registered"),
        ("APPOINTMENT", "Appointment Confirmed"),
        ("ARRIVED", "Farmer Arrived"),
        ("VERIFICATION", "Verification"),
        ("QUALITY", "Quality Check"),
        ("WEIGHING", "Weighing"),
        ("PROCURED", "Procurement Confirmed"),
        ("PAYMENT_PROCESSING", "Payment Processing"),
        ("PAYMENT_COMPLETED", "Payment Completed"),
    ]

    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="procurement_records",
    )
    crop_name = models.CharField(max_length=100)
    registered_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    actual_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=20, default="Quintals")

    center_name = models.CharField(max_length=150, default="Lucknow Procurement Hub")
    counter_number = models.CharField(max_length=20, default="Counter 2")
    token_number = models.CharField(max_length=50, default="A-104")
    appointment_date = models.CharField(max_length=100, default="12 September 2026, 10:30 AM")

    current_stage = models.CharField(max_length=30, choices=STAGE_CHOICES, default="WEIGHING")

    # Verification
    is_identity_verified = models.BooleanField(default=True)
    is_produce_verified = models.BooleanField(default=True)
    is_request_verified = models.BooleanField(default=True)
    verified_by = models.CharField(max_length=100, default="Officer R. Sharma")

    # Quality Check
    quality_grade = models.CharField(max_length=10, default="Grade A")
    moisture_content = models.CharField(max_length=20, default="11.5%")
    quality_status = models.CharField(max_length=50, default="Good")
    officer_remarks = models.TextField(default="Produce meets procurement standards")

    # Financials
    rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=2275.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=110692.50)
    payment_status = models.CharField(max_length=30, default="Processing")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.crop_name} - {self.farmer.username} ({self.get_current_stage_display()})"
