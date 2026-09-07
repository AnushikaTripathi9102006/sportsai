from django.contrib import admin
from .models import (
    ProcurementCenter,
    ProcurementRecord,
    QualityAssessment,
    WeighingRecord,
    ProcurementBill,
    PaymentRecord,
    ProcurementAuditLog,
)


@admin.register(ProcurementCenter)
class ProcurementCenterAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "district",
        "tehsil_block",
        "crops_handled",
        "capacity_quintals",
        "queue_status",
        "distance_km",
        "is_active",
    )
    list_filter = ("is_active", "queue_status", "district")
    search_fields = ("name", "code", "district", "tehsil_block", "crops_handled", "address")
    ordering = ("district", "name")


@admin.register(ProcurementRecord)
class ProcurementRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "token_number",
        "farmer",
        "crop_name",
        "registered_quantity",
        "center_display_name",
        "current_stage",
        "created_at",
    )
    list_filter = ("current_stage", "crop_name", "center")
    search_fields = ("farmer__username", "token_number", "crop_name", "center_name")


admin.site.register(QualityAssessment)
admin.site.register(WeighingRecord)
admin.site.register(ProcurementBill)
admin.site.register(PaymentRecord)
admin.site.register(ProcurementAuditLog)
