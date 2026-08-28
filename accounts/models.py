from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):

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

    is_approved = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"