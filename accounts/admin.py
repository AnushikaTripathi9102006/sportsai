from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "is_approved",
        "phone",
        "village",
        "district",
        "preferred_language",
    )

    list_filter = (
        "role",
        "district",
        "preferred_language",
    )

    search_fields = (
        "user__username",
        "user__email",
        "phone",
        "village",
        "district",
    )