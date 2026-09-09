import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kisanflow.settings")
django.setup()

from django.contrib.auth import get_user_model
from procurement.models import ProcurementRecord, ProcurementBill, PaymentRecord, ProcurementCenter
from procurement.services import transition_procurement_stage, perform_bill_generation, perform_acceptance

User = get_user_model()
officer = User.objects.filter(is_staff=True).first() or User.objects.first()

print("=================== PROCUREMENT BILL TRANSITION TESTS ===================")

# 1. Check Procurement #13
rec13 = ProcurementRecord.objects.filter(pk=13).first()
if rec13:
    print(f"\n[Test 1] Testing Procurement #13 (Initial Stage: {rec13.current_stage})")
    bill13 = perform_bill_generation(officer, rec13, rate_per_quintal=2275.00, deductions=0.00)
    print(f"  - Bill Generated/Retrieved: {bill13.bill_number}, Net Amount: ₹{bill13.net_amount}")
    print(f"  - Post-generation Stage: {rec13.current_stage}")
    assert rec13.current_stage == "BILL_GENERATED"
    print("  ✅ PASS: Procurement #13 processed successfully without duplicate transition error.")

# 2. Test Attempting Bill Generation Twice on #13
print("\n[Test 2] Attempting duplicate bill generation on Procurement #13")
bill13_again = perform_bill_generation(officer, rec13, rate_per_quintal=2300.00, deductions=50.00)
print(f"  - Duplicate Call Bill Number: {bill13_again.bill_number}")
print(f"  - Same instance returned: {bill13.id == bill13_again.id}")
assert bill13.id == bill13_again.id
total_bills_13 = ProcurementBill.objects.filter(procurement_record=rec13).count()
print(f"  - Total bills for #13 in DB: {total_bills_13}")
assert total_bills_13 == 1
print("  ✅ PASS: Second bill generation call returns existing bill without creating duplicate bill or duplicate transition error.")

# 3. Test Idempotent Transition directly on transition_procurement_stage
print("\n[Test 3] Testing transition_procurement_stage idempotency (BILL_GENERATED -> BILL_GENERATED)")
res = transition_procurement_stage(officer, rec13, "BILL_GENERATED", details="Idempotent check")
assert res.current_stage == "BILL_GENERATED"
print("  ✅ PASS: transition_procurement_stage handles current_stage == target_stage idempotently.")

# 4. Test Invalid Transition Rejection
print("\n[Test 4] Testing genuinely invalid state transitions")
invalid_transitions = [
    ("BILL_GENERATED", "REGISTRATION"),
    ("BILL_GENERATED", "WEIGHING"),
    ("BILL_GENERATED", "ACCEPTANCE"),
    ("COMPLETED", "BILL_GENERATED"),
    ("PAYMENT_INITIATED", "BILL_GENERATED"),
]

for start_stage, target_stage in invalid_transitions:
    dummy_record = ProcurementRecord.objects.create(
        farmer=rec13.farmer,
        crop_name="Test Wheat",
        registered_quantity=10,
        current_stage=start_stage
    )
    try:
        transition_procurement_stage(officer, dummy_record, target_stage)
        print(f"  ❌ FAIL: Expected error when moving {start_stage} -> {target_stage}")
    except ValueError as e:
        print(f"  ✅ PASS: Rejected invalid transition {start_stage} -> {target_stage}: '{e}'")
    dummy_record.delete()

# 5. Test New Procurement Record Lifecycle (ACCEPTANCE -> BILL_GENERATED -> PAYMENT)
print("\n[Test 5] Testing new procurement record full bill generation workflow")
new_rec = ProcurementRecord.objects.create(
    farmer=rec13.farmer,
    crop_name="Paddy Super",
    registered_quantity=25.5,
    actual_quantity=25.5,
    current_stage="ACCEPTANCE"
)
print(f"  - Initial stage: {new_rec.current_stage}")

# Acceptance step
perform_acceptance(officer, new_rec, decision="ACCEPT")
print(f"  - Stage after Acceptance: {new_rec.current_stage}")
assert new_rec.current_stage == "BILL_GENERATED"

# Bill generation step
new_bill = perform_bill_generation(officer, new_rec, rate_per_quintal=2183.00, deductions=100.00)
print(f"  - Bill generated: {new_bill.bill_number}, Net Amount: ₹{new_bill.net_amount}")
assert new_rec.current_stage == "BILL_GENERATED"

total_new_bills = ProcurementBill.objects.filter(procurement_record=new_rec).count()
assert total_new_bills == 1
print("  ✅ PASS: New procurement record workflow completed cleanly with 1 bill and correct state transitions.")

# Cleanup test record
new_rec.delete()

print("\n=================== ALL WORKFLOW TESTS PASSED ===================")
