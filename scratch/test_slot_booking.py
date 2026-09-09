import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from produce.models import Produce
from procurement.models import ProcurementCenter, ProcurementRecord
from appointments.models import Appointment

User = get_user_model()

def test_booking_flow():
    print("=" * 70)
    print("🧪 TESTING APPOINTMENT BOOKING FLOW (produce_id=13 & center_id=203)")
    print("=" * 70)

    client = Client()

    # 1. Setup farmer user
    farmer, _ = User.objects.get_or_create(username="test_slot_farmer")
    client.force_login(farmer)

    # 2. Get or create center
    center = ProcurementCenter.objects.filter(pk=203, is_active=True).first()
    if not center:
        center = ProcurementCenter.objects.create(
            pk=203,
            name="Test Barabanki Procurement Center",
            district="Barabanki",
            address="Mandi Yard, Barabanki",
            crops_handled="Wheat, Paddy, Mustard",
        )
    print(f"  🏢 Center: ID={center.id}, Name='{center.name}'")

    # 3. Get or create produce batch 13
    produce = Produce.objects.filter(pk=13, farmer=farmer).first()
    if not produce:
        produce = Produce.objects.create(
            pk=13,
            farmer=farmer,
            crop_name="Paddy (Rice)",
            quantity=20.0,
            unit="QUINTAL",
            harvest_date="2026-09-01",
            district="Barabanki",
            status="REQUESTED",
        )
    else:
        produce.status = "REQUESTED"
        produce.save()
    print(f"  🌾 Produce: ID={produce.id}, Crop='{produce.crop_name}', Farmer='{farmer.username}'")

    # 4. Clear old confirmed appointments for test idempotency
    Appointment.objects.filter(produce=produce).delete()

    # 5. GET request to /appointments/book/?produce_id=13&center_id=203
    url = f"/appointments/book/?produce_id={produce.id}&center_id={center.id}"
    response = client.get(url)
    print(f"  GET {url} -> Status {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Verify context
    ctx_center = response.context["center"]
    ctx_produce = response.context["selected_produce"]
    slots = response.context["slots_availability"]
    print(f"  Context Center: '{ctx_center.name if ctx_center else None}'")
    print(f"  Context Produce: '{ctx_produce.crop_name if ctx_produce else None}'")
    print(f"  Available Slots Count: {len(slots)}")
    assert ctx_center and ctx_center.id == center.id, "Center missing from GET context"

    # 6. POST request action=review (selecting first available slot)
    available_slot = next(s for s in slots if s["is_available"])
    slot_code = available_slot["code"]
    appt_date = response.context["selected_date"].strftime("%Y-%m-%d")
    print(f"  Selecting Slot: '{slot_code}' for Date '{appt_date}'")

    post_data_review = {
        "action": "review",
        "produce_id": produce.id,
        "center_id": center.id,
        "appointment_date": appt_date,
        "appointment_time_slot": slot_code,
    }
    response_review = client.post("/appointments/book/", post_data_review)
    print(f"  POST action=review -> Status {response_review.status_code}")
    assert response_review.status_code == 200, f"Review expected 200, got {response_review.status_code}"
    assert "confirm.html" in [t.name for t in response_review.templates], "Review should render confirm.html"

    # 7. POST request action=confirm (locking appointment)
    post_data_confirm = {
        "action": "confirm",
        "produce_id": produce.id,
        "center_id": center.id,
        "appointment_date": appt_date,
        "appointment_time_slot": slot_code,
    }
    response_confirm = client.post("/appointments/book/", post_data_confirm)
    print(f"  POST action=confirm -> Status {response_confirm.status_code}")
    assert response_confirm.status_code == 302, f"Confirm expected redirect (302), got {response_confirm.status_code}"

    # 8. Verify DB Appointment Creation
    created_appt = Appointment.objects.filter(
        farmer=farmer,
        produce=produce,
        procurement_center=center,
        appointment_date=appt_date,
        appointment_time_slot=slot_code,
        status="CONFIRMED",
    ).first()

    assert created_appt is not None, "Appointment was not created in database!"
    print(f"  ✅ SUCCESS: Appointment created with ID={created_appt.id}, Code='{created_appt.appointment_code}', Slot='{created_appt.appointment_time_slot}'")

    # 9. Verify Procurement Record & Token sync
    rec = ProcurementRecord.objects.filter(produce=produce, farmer=farmer).first()
    assert rec is not None and rec.center == center, "Procurement record not synced with center"
    print(f"  ✅ SUCCESS: Procurement Record updated: Stage='{rec.current_stage}', Center='{rec.center.name}'")

    print("=" * 70)
    print("🎉 ALL TEST SUITE CHECKS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_booking_flow()
