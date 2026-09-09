import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kisanflow.settings")
django.setup()

from procurement.models import ProcurementRecord, ProcurementBill, PaymentRecord

print("--- Procurement Records & Bills Check ---")
rec13 = ProcurementRecord.objects.filter(pk=13).first()
if rec13:
    print(f"Record 13: ID={rec13.id}, Stage={rec13.current_stage}, Crop={rec13.crop_name}, Farmer={rec13.farmer.username}")
    bills = ProcurementBill.objects.filter(procurement_record=rec13)
    print(f"Bills count for Record 13: {bills.count()}")
    for b in bills:
        print(f"  Bill ID={b.id}, Bill No={b.bill_number}, Net Amount={b.net_amount}, Generated At={b.generated_at}")
    
    payments = PaymentRecord.objects.filter(procurement_record=rec13)
    print(f"Payments count for Record 13: {payments.count()}")
    for p in payments:
        print(f"  Payment ID={p.id}, Status={p.payment_status}, Bill ID={p.bill_id}")
else:
    print("Record 13 not found")

# Check all duplicate bills in system
from django.db.models import Count
dups = ProcurementBill.objects.values('procurement_record').annotate(cnt=Count('id')).filter(cnt__gt=1)
print(f"Duplicate bills count in DB: {dups.count()}")
if dups.count() > 0:
    print(f"Duplicate bill procurement IDs: {list(dups)}")
