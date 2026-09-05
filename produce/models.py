from django.conf import settings
from django.db import models


class MSPCrop(models.Model):
    objects = models.Manager()

    CATEGORY_CHOICES = [
        ("KHARIF", "Kharif Crop"),
        ("RABI", "Rabi Crop"),
        ("COMMERCIAL", "Commercial / Other Crop"),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="KHARIF",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "MSP Crop"
        verbose_name_plural = "MSP Crops"
        ordering = ["name"]

    def __str__(self):
        return str(self.name)


class Produce(models.Model):
    objects = models.Manager()

    STATUS_CHOICES = [
        ("AVAILABLE", "Available"),
        ("REQUESTED", "Procurement Requested"),
        ("PROCURED", "Procured"),
    ]

    UNIT_CHOICES = [
        ("KG", "Kilograms"),
        ("QUINTAL", "Quintals"),
        ("TONNE", "Tonnes"),
    ]

    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="produce",
    )

    crop_name = models.CharField(max_length=100)

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
    )

    harvest_date = models.DateField()

    district = models.CharField(
        max_length=100,
        default="Lucknow",
        verbose_name="District (Uttar Pradesh)",
        help_text="District used to locate nearest procurement centers in UP",
    )

    address = models.TextField(
        blank=True,
        default="",
        verbose_name="Farm / Pickup Address",
        help_text="Address used to calculate nearest procurement center",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="AVAILABLE",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.crop_name} - {self.quantity} {self.get_unit_display()}"