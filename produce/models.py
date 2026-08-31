from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models


class Produce(models.Model):
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

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="AVAILABLE",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.crop_name} - {self.quantity} {self.get_unit_display()}"