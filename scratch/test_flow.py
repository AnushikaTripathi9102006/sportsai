import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from datetime import date, timedelta
from django.contrib.auth import get_user_model
from produce.models import Produce
from procurement.models import ProcurementCenter, ProcurementRecord
from procurement.recommendation_engine import get_recommended_centers
from appointments.models import Appointment
from tokens.models import Token
from accounts.models import Profile

User = get_user_model()

def test_full_farmer_journey():
    print("=" * 70)
    print("🚀 TESTING FARMER-CONTROLLED CENTER SELECTION + APPOINTMENT + RESCHEDULING")
    print("=" * 70)

    # 1. Create or get test farmer
    farmer, _ = User.objects.get_or_create(username="test_farmer_ramesh", defaults={"first_name": "Ramesh", "last_name": "Kumar"})
    farmer_profile, _ = Profile.objects.get_or_create(user=farmer, defaults={"role": "FARMER", "district": "Lucknow"})

    # 2. Register produce: Wheat, 50 Quintals, Lucknow
    produce, _ = Produce.objects.get_or_create(
        farmer=farmer,
        crop_name="Wheat",
        defaults={
            "quantity": 50.00,
            "unit": "QUINTAL",
            "harvest_date": date.today(),
            "district": "Lucknow",
            "status": "REQUESTED"
        }
    )
    print(f"✅ Farmer registered produce: {produce.crop_name} - {produce.quantity} Quintals in {produce.district}")

    # 3. Create or ensure test procurement centers
    center_a, _ = ProcurementCenter.objects.get_or_create(
        name="Lucknow Wheat Procurement Hub",
        district="Lucknow",
        defaults={
            "crops_handled": "Wheat, Paddy",
            "distance_km": 4.5,
            "queue_status": "LOW",
            "is_active": True
        }
    )
    center_b, _ = ProcurementCenter.objects.get_or_create(
        name="Kanpur Road Procurement Center",
        district="Lucknow",
        defaults={
            "crops_handled": "Wheat, Mustard",
            "distance_km": 9.2,
            "queue_status": "MEDIUM",
            "is_active": True
        }
    )
    print(f"✅ Active Centers: 1. {center_a.name} ({center_a.distance_km}km) | 2. {center_b.name} ({center_b.distance_km}km)")

    # 4. Test Recommendation Engine
    top_rec, ranked = get_recommended_centers(produce=produce, farmer=farmer, target_district="Lucknow")
    print("\n🤖 RECOMMENDATION ENGINE RESULT:")
    print(f"   🥇 Top Recommendation: {top_rec.name} (Score: {top_rec.recommendation_score}) Badge: {top_rec.recommendation_badge}")
    print("   Reasons:")
    for r in top_rec.reasons:
        print(f"     - {r}")

    # 5. Farmer explicitly selects Center A
    rec, _ = ProcurementRecord.objects.get_or_create(
        farmer=farmer,
        produce=produce,
        defaults={"crop_name": produce.crop_name, "registered_quantity": produce.quantity, "center": center_a, "current_stage": "REGISTRATION"}
    )
    rec.center = center_a
    rec.save()
    print(f"\n👨‍🌾 Farmer explicitly selected center: {rec.center.name}")

    # 6. Farmer books appointment at Center A
    today = date.today()
    appt_date = today + timedelta(days=2)
    slot = "10:00 AM - 11:00 AM"

    # Remove any existing appointments for clean test
    Appointment.objects.filter(farmer=farmer, produce=produce).delete()

    appointment = Appointment.objects.create(
        farmer=farmer,
        produce=produce,
        procurement_record=rec,
        procurement_center=center_a,
        appointment_date=appt_date,
        appointment_time_slot=slot,
        status="CONFIRMED"
    )
    rec.appointment_date = f"{appt_date.strftime('%d %b %Y')} ({slot})"
    rec.current_stage = "APPOINTMENT"
    rec.save()

    # Generate token
    from tokens.services import generate_token_for_appointment
    token = generate_token_for_appointment(appointment)
    print(f"📅 Appointment Confirmed: {appointment.appointment_code} on {appt_date} ({slot})")
    print(f"🎟️ Token Generated: {token.token_number} (Status: {token.status})")

    # 7. Check Officer Dashboard at Center A
    officer_a, _ = User.objects.get_or_create(username="officer_center_a", defaults={"first_name": "Officer", "last_name": "Sharma"})
    Profile.objects.get_or_create(user=officer_a, defaults={"role": "OFFICER", "assigned_center": center_a})

    from procurement.views import _get_officer_records
    records_at_a = _get_officer_records(center_a)
    print(f"\n👮 Officer at Center A sees {records_at_a.count()} farmer registration(s):")
    for r in records_at_a:
        print(f"   - Farmer: {r.farmer.username} | Crop: {r.crop_name} | Token: {r.token_number} | Stage: {r.current_stage}")

    assert records_at_a.filter(pk=rec.pk).exists(), "Officer A must see farmer registration"

    # 8. FARMER RESCHEDULES APPOINTMENT -> Switches to Center B
    print("\n🔄 FARMER CANCELED / RESCHEDULES APPOINTMENT TO CENTER B...")
    new_appt_date = today + timedelta(days=4)
    new_slot = "11:00 AM - 12:00 PM"

    # Cancel old appointment and old token
    appointment.status = "CANCELLED"
    appointment.save()
    token.status = "CANCELLED"
    token.save()

    # Create new appointment at Center B
    new_appointment = Appointment.objects.create(
        farmer=farmer,
        produce=produce,
        procurement_record=rec,
        procurement_center=center_b,
        appointment_date=new_appt_date,
        appointment_time_slot=new_slot,
        status="CONFIRMED"
    )

    rec.center = center_b
    rec.center_name = center_b.name
    rec.appointment_date = f"{new_appt_date.strftime('%d %b %Y')} ({new_slot})"
    rec.save()

    # Generate new token for new appointment
    new_token = generate_token_for_appointment(new_appointment)

    print(f"📅 Rescheduled Appointment: {new_appointment.appointment_code} at {center_b.name} on {new_appt_date} ({new_slot})")
    print(f"🎟️ New Token Generated: {new_token.token_number}")
    print(f"❌ Old Token Status: {token.status}")

    # 9. Verify Officer Visibility After Rescheduling
    officer_b, _ = User.objects.get_or_create(username="officer_center_b", defaults={"first_name": "Officer", "last_name": "Verma"})
    Profile.objects.get_or_create(user=officer_b, defaults={"role": "OFFICER", "assigned_center": center_b})

    records_at_b = _get_officer_records(center_b)
    records_at_a_after = _get_officer_records(center_a)

    print(f"\n👮 Officer at Center B (NEW) sees {records_at_b.count()} registration(s):")
    for r in records_at_b:
        print(f"   - Farmer: {r.farmer.username} | Center: {r.center.name} | Token: {r.token_number}")

    print(f"👮 Officer at Center A (OLD) active registrations count: {records_at_a_after.filter(center=center_a).count()}")

    assert records_at_b.filter(pk=rec.pk).exists(), "Officer B MUST see rescheduled farmer registration"
    assert not records_at_a_after.filter(center=center_a, pk=rec.pk).exists(), "Officer A MUST NO LONGER see registration as active center"

    # 10. Check Notifications
    from notifications.models import Notification
    farmer_notifs = Notification.objects.filter(user=farmer).order_by("-created_at")
    print(f"\n🔔 Farmer received {farmer_notifs.count()} notifications:")
    for n in farmer_notifs[:5]:
        print(f"   - [{n.notification_type}] {n.title}: {n.message}")

    print("\n" + "=" * 70)
    print("🎉 ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_full_farmer_journey()
