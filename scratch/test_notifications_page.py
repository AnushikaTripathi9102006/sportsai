import os
import sys
import django
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from produce.models import Produce
from procurement.models import ProcurementCenter, ProcurementRecord, ProcurementBill, PaymentRecord
from appointments.models import Appointment
from tokens.models import Token
from notifications.models import Notification
from accounts.models import Profile

User = get_user_model()

def test_notifications_full_flow():
    print("=" * 70)
    print("🧪 TESTING NOTIFICATION PAGE & AUTOMATIC STEP SYNCING")
    print("=" * 70)

    # 1. Get or create test farmer
    farmer, _ = User.objects.get_or_create(username="notif_test_farmer", defaults={"first_name": "Ramesh", "last_name": "Singh"})
    Profile.objects.get_or_create(user=farmer, defaults={"role": "FARMER", "district": "Lucknow"})

    # Clean up past test notifications for clean verification
    Notification.objects.filter(user=farmer).delete()

    # 2. Register produce (Step 1)
    produce, _ = Produce.objects.get_or_create(
        farmer=farmer,
        crop_name="Wheat MSP Grade A",
        defaults={
            "quantity": 100.00,
            "unit": "QUINTAL",
            "harvest_date": date.today(),
            "district": "Lucknow",
            "status": "APPROVED"
        }
    )

    # 3. Create center & record (Step 2: Center Assignment)
    center, _ = ProcurementCenter.objects.get_or_create(
        name="Lucknow Central Hub",
        district="Lucknow",
        defaults={"distance_km": 3.2, "queue_status": "LOW"}
    )
    rec, _ = ProcurementRecord.objects.get_or_create(
        farmer=farmer,
        produce=produce,
        defaults={
            "crop_name": "Wheat MSP Grade A",
            "registered_quantity": 100.00,
            "actual_quantity": 98.50,
            "center": center,
            "token_number": "LUC-999",
            "current_stage": "PAYMENT_RECEIVED",
            "quality_grade": "Grade A (FAQ)",
            "moisture_content": "11.2%",
            "total_amount": 224087.50
        }
    )

    # 4. Appointment & Token (Step 3 & 4)
    appt, _ = Appointment.objects.get_or_create(
        farmer=farmer,
        produce=produce,
        procurement_record=rec,
        defaults={
            "procurement_center": center,
            "appointment_date": date.today(),
            "appointment_time_slot": "10:00 AM - 11:00 AM",
            "status": "CONFIRMED"
        }
    )
    tok, _ = Token.objects.get_or_create(
        appointment=appt,
        defaults={
            "farmer": farmer,
            "produce": produce,
            "procurement_center": center,
            "date": date.today(),
            "sequence_number": 99,
            "token_number": "LUC-999",
            "counter_number": "Counter 1",
            "status": "COMPLETED"
        }
    )

    # 5. Bill & Payment (Step 8 & 9)
    bill, _ = ProcurementBill.objects.get_or_create(
        bill_number="BILL-9999",
        procurement_record=rec,
        defaults={
            "quantity_quintals": 98.50,
            "rate_per_quintal": 2275.00,
            "gross_amount": 224087.50,
            "deductions": 0.00,
            "net_amount": 224087.50,
            "generated_by": farmer
        }
    )
    payment, _ = PaymentRecord.objects.get_or_create(
        procurement_record=rec,
        bill=bill,
        defaults={
            "payment_status": "RECEIVED",
            "transaction_reference": "TXN999988887777"
        }
    )

    # Now make GET request to /notifications/
    client = Client()
    client.force_login(farmer)
    response = client.get("/notifications/")

    print(f"📡 Request to /notifications/ status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify notifications were populated in DB
    farmer_notifs = Notification.objects.filter(user=farmer).order_by("-created_at")
    print(f"📊 Total notifications created after view access: {farmer_notifs.count()}")

    for idx, n in enumerate(farmer_notifs, 1):
        print(f"   {idx}. [{n.notification_type}] {n.title}")

    # Check HTML response content contains key notifications
    content = response.content.decode("utf-8")
    assert "Live Notifications" in content, "Page missing heading"
    assert "Wheat MSP Grade A" in content, "Page missing crop notifications"
    assert "Lucknow Central Hub" in content, "Page missing center notification"

    print("=" * 70)
    print("🎉 NOTIFICATION PAGE & STEP SYNCING VERIFIED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_notifications_full_flow()
