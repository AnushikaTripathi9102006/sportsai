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

    farmer_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
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
            last_farmer = Profile.objects.filter(
                role="FARMER"
            ).order_by("-id").first()

        if last_farmer and last_farmer.farmer_id:
            last_number = int(
                last_farmer.farmer_id.split("-")[1]
            )
            next_number = last_number + 1
        else:
            next_number = 1

        self.farmer_id = f"FAR-{next_number:04d}"

        super().save(*args, **kwargs)