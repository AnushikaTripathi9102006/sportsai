import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from procurement.models import ProcurementRecord, ProcurementCenter

def check_rec():
    print("=" * 70)
    print("🔍 INSPECTING PROCUREMENT RECORD 13")
    print("=" * 70)

    rec = ProcurementRecord.objects.filter(pk=13).first()
    if rec:
        print(f"Record ID: {rec.id}")
        print(f"Farmer: {rec.farmer.username} ({rec.farmer.get_full_name()})")
        print(f"Crop: {rec.crop_name}, Quantity: {rec.registered_quantity} {rec.unit}")
        print(f"Center: {rec.center.name if rec.center else None} (ID={rec.center.id if rec.center else None})")
        print(f"Stage: {rec.current_stage}")
        print(f"Token: {rec.token_number}")
        print(f"Vehicle: {rec.vehicle_number}")
    else:
        print("Record 13 NOT FOUND in database!")

    print("\nAll Procurement Records in DB:")
    for r in ProcurementRecord.objects.all():
        print(f"  ID={r.id} | Farmer={r.farmer.username} | Crop={r.crop_name} | Stage={r.current_stage} | Center={r.center.name if r.center else 'None'}")

    print("=" * 70)

if __name__ == "__main__":
    check_rec()
