import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models import Profile
from produce.models import Produce
from procurement.models import ProcurementCenter, ProcurementRecord

User = get_user_model()

def test_gate_entry():
    print("=" * 70)
    print("🧪 TESTING GATE ENTRY WORKFLOW (record_id=13)")
    print("=" * 70)

    client = Client()

    # 1. Setup Officer
    officer, _ = User.objects.get_or_create(username="test_gate_officer")
    center, _ = ProcurementCenter.objects.get_or_create(
        pk=203,
        defaults={
            "name": "Barabanki Central Grain Collection Centre",
            "district": "Barabanki",
            "address": "Mandi Yard, Barabanki",
            "crops_handled": "Wheat, Paddy, Mustard",
        }
    )
    profile, _ = Profile.objects.get_or_create(user=officer, defaults={"role": "OFFICER", "assigned_center": center, "is_approved": True})
    profile.role = "OFFICER"
    profile.assigned_center = center
    profile.is_approved = True
    profile.save()
    client.force_login(officer)
    print(f"  Officer: '{officer.username}', Center: '{center.name}'")

    # 2. Setup Farmer and Record 13
    farmer, _ = User.objects.get_or_create(username="test_gate_farmer")
    Profile.objects.get_or_create(user=farmer, defaults={"role": "FARMER", "farmer_id": "FAR-0013", "district": "Barabanki"})

    produce, _ = Produce.objects.get_or_create(
        pk=13,
        defaults={
            "farmer": farmer,
            "crop_name": "Paddy (Rice)",
            "quantity": 20.0,
            "unit": "QUINTAL",
            "harvest_date": "2026-09-01",
            "district": "Barabanki",
            "status": "REQUESTED",
        }
    )

    record, _ = ProcurementRecord.objects.get_or_create(
        pk=13,
        defaults={
            "farmer": farmer,
            "produce": produce,
            "crop_name": produce.crop_name,
            "registered_quantity": produce.quantity,
            "unit": "Quintals",
            "center": center,
            "center_name": center.name,
            "token_number": "A-101",
            "current_stage": "APPOINTMENT",
        }
    )
    record.center = center
    record.save()
    print(f"  Record 13: Farmer='{record.farmer.username}', Crop='{record.crop_name}', Stage='{record.current_stage}'")

    # 3. GET /procurement/officer/gate-entry/?record_id=13
    url = "/procurement/officer/gate-entry/?record_id=13"
    response = client.get(url)
    print(f"  GET {url} -> Status {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    ctx_selected = response.context["selected_record"]
    ctx_pending = list(response.context["pending_records"])
    print(f"  Selected Record in Context: ID={ctx_selected.id if ctx_selected else None}")
    print(f"  Pending Records Count: {len(ctx_pending)}")
    assert ctx_selected and ctx_selected.id == 13, "Record 13 missing from selected_record context"
    assert any(r.id == 13 for r in ctx_pending), "Record 13 missing from pending_records list"

    # 4. POST Gate Entry Confirmation
    post_data = {
        "record_id": 13,
        "vehicle_number": "UP-32-AB-1234",
        "notes": "Farmer arrived at Counter 1 gate.",
    }
    post_resp = client.post("/procurement/officer/gate-entry/", post_data)
    print(f"  POST /procurement/officer/gate-entry/ -> Status {post_resp.status_code}")
    assert post_resp.status_code == 302, f"POST expected redirect (302), got {post_resp.status_code}"

    # 5. Verify Record State Updated
    record.refresh_from_db()
    print(f"  Post-Entry Record State: Stage='{record.current_stage}', Vehicle='{record.vehicle_number}'")
    assert record.current_stage == "GATE_ENTRY", f"Expected stage GATE_ENTRY, got {record.current_stage}"
    assert record.vehicle_number == "UP-32-AB-1234", "Vehicle number was not saved"

    print("=" * 70)
    print("🎉 ALL GATE ENTRY CHECKS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_gate_entry()
