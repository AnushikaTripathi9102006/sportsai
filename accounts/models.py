import re

from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    objects = models.Manager()

    ROLE_CHOICES = [
        ("FARMER", "Farmer"),
        ("OFFICER", "Procurement Officer"),
        ("ADMIN", "Administrator"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="FARMER"
    )

    farmer_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    assigned_center = models.ForeignKey(
        "procurement.ProcurementCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="officers",
    )

    is_approved = models.BooleanField(default=True)

    phone = models.CharField(
        max_length=15,
        blank=True
    )

    village = models.CharField(
        max_length=100,
        blank=True
    )

    district = models.CharField(
        max_length=100,
        blank=True
    )

    preferred_language = models.CharField(
        max_length=20,
        default="Hindi"
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    def save(self, *args, **kwargs):
        if self.role == "FARMER" and not self.farmer_id:
            farmer_numbers = [
                int(match.group(1))
                for f_id in Profile.objects.filter(
                    farmer_id__startswith="FAR-",
                ).values_list("farmer_id", flat=True)
                if (match := re.fullmatch(r"FAR-(\d+)", str(f_id)))
            ]
            next_number = max(farmer_numbers, default=0) + 1

            self.farmer_id = f"FAR-{next_number:04d}"

        super().save(*args, **kwargs)