from django.contrib import admin
from .models import MSPCrop, Produce


@admin.register(MSPCrop)
class MSPCropAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("name",)


@admin.register(Produce)
class ProduceAdmin(admin.ModelAdmin):
    list_display = ("crop_name", "farmer", "quantity", "unit", "status", "created_at")
    list_filter = ("status", "unit")
    search_fields = ("crop_name", "farmer__username")
