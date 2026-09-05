from django.conf import settings
from django.db import models


class ProcurementCenter(models.Model):
    objects = models.Manager()

    QUEUE_CHOICES = [
        ("LOW", "Low Queue"),
        ("MEDIUM", "Medium Queue"),
        ("HIGH", "High Queue"),
    ]

    code = models.CharField(max_length=50, blank=True, default="")
    name = models.CharField(max_length=150)
    district = models.CharField(max_length=100)
    tehsil_block = models.CharField(max_length=100, blank=True, default="")
    address = models.TextField()
    contact_number = models.CharField(max_length=20, default="+91 94150 12345")
    operating_hours = models.CharField(max_length=50, default="08:00 AM - 05:00 PM")
    crops_handled = models.CharField(max_length=200, default="Wheat, Paddy, Mustard, Gram")
    queue_status = models.CharField(max_length=10, choices=QUEUE_CHOICES, default="LOW")
    distance_km = models.DecimalField(max_digits=5, decimal_places=1, default=4.5)
    capacity_quintals = models.IntegerField(default=5000)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Procurement Center"
        verbose_name_plural = "Procurement Centers"
        ordering = ["district", "name"]

    def __str__(self):
        return f"{self.name} ({self.district})"


class ProcurementRecord(models.Model):
    objects = models.Manager()

    STAGE_CHOICES = [
        ("REGISTRATION", "Produce Registered"),
        ("APPOINTMENT", "Appointment Confirmed"),
        ("GATE_ENTRY", "Gate Entry"),
        ("QUALITY_CHECK", "Quality Check"),
        ("WEIGHING", "Weighing"),
        ("ACCEPTANCE", "Acceptance"),
        ("BILL_GENERATED", "Bill Generated"),
        ("PAYMENT_INITIATED", "Payment Initiated"),
        ("PAYMENT_RECEIVED", "Payment Received"),
        ("COMPLETED", "Procurement Completed"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="procurement_records",
    )
    produce = models.ForeignKey(
        "produce.Produce",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procurement_records",
    )
    center = models.ForeignKey(
        ProcurementCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procurement_records",
    )

    crop_name = models.CharField(max_length=100)
    registered_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    actual_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=20, default="Quintals")

    center_name = models.CharField(max_length=150, default="Lucknow Procurement Hub")
    counter_number = models.CharField(max_length=20, default="Counter 1")
    token_number = models.CharField(max_length=50, default="A-101")
    vehicle_number = models.CharField(max_length=50, blank=True, default="")
    appointment_date = models.CharField(max_length=100, default="Today, 10:00 AM")

    current_stage = models.CharField(max_length=30, choices=STAGE_CHOICES, default="REGISTRATION")

    # Verification
    is_identity_verified = models.BooleanField(default=False)
    is_produce_verified = models.BooleanField(default=False)
    is_request_verified = models.BooleanField(default=False)
    verified_by = models.CharField(max_length=100, default="Officer R. Sharma")
    gate_entry_at = models.DateTimeField(null=True, blank=True)

    # Quality Check Summary
    quality_grade = models.CharField(max_length=20, default="Grade A")
    moisture_content = models.CharField(max_length=20, default="11.5%")
    quality_status = models.CharField(max_length=50, default="Pending")
    officer_remarks = models.TextField(blank=True, default="")
    rejection_reason = models.TextField(blank=True, default="")

    # Financials
    rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=2275.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=30, default="Pending")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        farmer_username = getattr(self.farmer, "username", str(self.farmer))
        return f"{self.crop_name} - {farmer_username} ({self.get_current_stage_display()})"

    @property
    def district(self):
        produce = getattr(self, "produce", None)
        if produce and getattr(produce, "district", None):
            return produce.district
        center = getattr(self, "center", None)
        if center and getattr(center, "district", None):
            return center.district
        return "Lucknow"

    @property
    def stage(self):
        return self.current_stage

    @property
    def estimated_quantity_quintals(self):
        return self.registered_quantity

    @property
    def actual_quantity_quintals(self):
        return self.actual_quantity

    @property
    def appointment_slot(self):
        return self.appointment_date



class QualityAssessment(models.Model):
    objects = models.Manager()

    RESULT_CHOICES = [
        ("PASSED", "Passed"),
        ("REJECTED", "Rejected"),
    ]

    GRADE_CHOICES = [
        ("GRADE_A", "Grade A (FAQ)"),
        ("GRADE_B", "Grade B"),
        ("GRADE_C", "Grade C"),
    ]

    procurement_record = models.OneToOneField(
        ProcurementRecord,
        on_delete=models.CASCADE,
        related_name="quality_assessment",
    )
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quality_assessments",
    )
    quality_grade = models.CharField(max_length=20, choices=GRADE_CHOICES, default="GRADE_A")
    moisture_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=11.50)
    foreign_matter_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    damaged_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.50)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default="PASSED")
    rejection_reason = models.TextField(blank=True, default="")
    remarks = models.TextField(blank=True, default="")
    inspected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quality {self.result} - {self.procurement_record.crop_name}"


class WeighingRecord(models.Model):
    objects = models.Manager()

    procurement_record = models.OneToOneField(
        ProcurementRecord,
        on_delete=models.CASCADE,
        related_name="weighing_record",
    )
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weighing_records",
    )
    gross_weight = models.DecimalField(max_digits=10, decimal_places=2)
    tare_weight = models.DecimalField(max_digits=10, decimal_places=2)
    net_weight = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, default="Quintals")
    remarks = models.TextField(blank=True, default="")
    weighed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Weighing {self.net_weight} {self.unit} - {self.procurement_record.crop_name}"


class ProcurementBill(models.Model):
    objects = models.Manager()

    bill_number = models.CharField(max_length=50, unique=True)
    procurement_record = models.OneToOneField(
        ProcurementRecord,
        on_delete=models.CASCADE,
        related_name="bill",
    )
    quantity_quintals = models.DecimalField(max_digits=10, decimal_places=2)
    rate_per_quintal = models.DecimalField(max_digits=10, decimal_places=2)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_bills",
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bill #{self.bill_number} - ₹{self.net_amount}"


class PaymentRecord(models.Model):
    objects = models.Manager()

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("INITIATED", "Initiated"),
        ("RECEIVED", "Received"),
        ("FAILED", "Failed"),
    ]

    procurement_record = models.OneToOneField(
        ProcurementRecord,
        on_delete=models.CASCADE,
        related_name="payment_record",
    )
    bill = models.OneToOneField(
        ProcurementBill,
        on_delete=models.CASCADE,
        related_name="payment_record",
    )
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    transaction_reference = models.CharField(max_length=100, blank=True, default="")
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_payments",
    )
    initiated_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment {self.payment_status} - #{self.bill.bill_number}"


class ProcurementAuditLog(models.Model):
    objects = models.Manager()

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    procurement_record = models.ForeignKey(
        ProcurementRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    center = models.ForeignKey(
        ProcurementCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    details = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        actor_username = getattr(self.actor, "username", str(self.actor))
        ts_str = self.timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(self.timestamp, 'strftime') else str(self.timestamp)
        return f"[{ts_str}] {actor_username} - {self.action}"
