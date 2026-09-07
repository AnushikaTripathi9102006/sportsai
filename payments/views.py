from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from produce.models import Produce


@login_required
def payments(request):
    from procurement.models import ProcurementRecord
    from procurement.services import sync_all_farmer_procurements

    sync_all_farmer_procurements()

    profile = getattr(request.user, "profile", None)

    records = ProcurementRecord.objects.filter(
        farmer=request.user
    ).select_related("produce", "center").prefetch_related("bill", "payment_record").order_by("-updated_at")

    history_records = []
    total_earned = 0.0
    pending_amount = 0.0
    paid_amount = 0.0
    last_payment_amount = 0.0
    last_payment_date = "--"

    current_payment = None

    for rec in records:
        bill = getattr(rec, "bill", None)
        payment_rec = getattr(rec, "payment_record", None)

        amt = float(bill.net_amount) if bill else float(rec.total_amount or 0.0)
        if amt == 0 and rec.registered_quantity and rec.rate_per_unit:
            amt = float(rec.registered_quantity * rec.rate_per_unit)

        st = payment_rec.get_payment_status_display() if payment_rec else rec.payment_status
        is_completed = (st in ["Received", "Completed", "PAYMENT_RECEIVED", "COMPLETED"]) or rec.current_stage in ["PAYMENT_RECEIVED", "COMPLETED"]

        if is_completed:
            paid_amount += amt
            total_earned += amt
            if last_payment_amount == 0 and amt > 0:
                last_payment_amount = amt
                last_payment_date = rec.updated_at.strftime("%d %b %Y")
        else:
            if amt > 0 or rec.current_stage in ["BILL_GENERATED", "PAYMENT_INITIATED", "ACCEPTANCE"]:
                pending_amount += amt

        item = {
            "id": rec.id,
            "date": rec.updated_at.strftime("%d %b %Y"),
            "crop": rec.crop_name,
            "quantity": f"{rec.actual_quantity or rec.registered_quantity} {rec.unit}",
            "amount": f"₹{amt:,.2f}",
            "amount_raw": amt,
            "status": "Completed" if is_completed else "Processing",
            "status_code": "COMPLETED" if is_completed else "PROCESSING",
            "badge_color": "green" if is_completed else "yellow",
            "receipt_available": is_completed or hasattr(rec, "bill"),
            "token_number": f"#{rec.token_number}",
            "center_name": rec.center_display_name,
            "rate": f"₹{bill.rate_per_quintal if bill else rec.rate_per_unit:,.2f} / {rec.unit}",
            "quality_grade": rec.quality_grade or "Grade A",
            "transaction_id": payment_rec.transaction_reference if (payment_rec and payment_rec.transaction_reference) else (f"TXN-{rec.id:06d}"),
            "stepper": [
                {"label": "Amount Calculated", "state": "done" if rec.current_stage in ["ACCEPTANCE", "BILL_GENERATED", "PAYMENT_INITIATED", "PAYMENT_RECEIVED", "COMPLETED"] else "current"},
                {"label": "Bill Generated", "state": "done" if rec.current_stage in ["BILL_GENERATED", "PAYMENT_INITIATED", "PAYMENT_RECEIVED", "COMPLETED"] else "pending"},
                {"label": "Processing", "state": "current" if rec.current_stage in ["PAYMENT_INITIATED", "BILL_GENERATED"] else ("done" if is_completed else "pending")},
                {"label": "Payment Completed", "state": "done" if is_completed else "pending"},
            ]
        }

        history_records.append(item)

        if not current_payment and not is_completed and amt > 0:
            current_payment = item

    if not current_payment and history_records:
        current_payment = history_records[0]

    overview = {
        "total_earned": f"₹{total_earned:,.2f}",
        "pending_amount": f"₹{pending_amount:,.2f}",
        "paid_amount": f"₹{paid_amount:,.2f}",
        "last_payment": f"₹{last_payment_amount:,.2f}" if last_payment_amount > 0 else "₹0.00",
        "last_payment_date": last_payment_date,
    }

    is_delayed = request.GET.get("delay", "0") == "1"
    smart_update = {
        "is_delayed": is_delayed,
        "title": "⚠️ PAYMENT DELAY" if is_delayed else "🤖 PAYMENT UPDATE",
        "message": (
            f"Your payout for {current_payment['crop'] if current_payment else 'crop'} is processing automatically via bank network queue."
            if is_delayed
            else f"Your active payout of {current_payment['amount'] if current_payment else '₹0'} for {current_payment['crop'] if current_payment else 'produce'} is currently processing."
        ),
    }

    return render(
        request,
        "payments/payments.html",
        {
            "farmer": request.user,
            "profile": profile,
            "overview": overview,
            "current_payment": current_payment,
            "smart_update": smart_update,
            "history_records": history_records,
        },
    )


@login_required
def payment_detail(request, payment_id):
    profile = getattr(request.user, "profile", None)

    all_payments = {
        1: {
            "id": 1,
            "crop": "Wheat",
            "registered_qty": "45.0 Quintals",
            "final_qty": "45.0 Quintal",
            "quality_grade": "Grade A",
            "rate": "₹2,666 / Quintal",
            "amount": "₹12,000",
            "status": "Processing",
            "status_code": "PROCESSING",
            "badge_color": "yellow",
            "expected_date": "05 Sep 2026",
            "procurement_center": "Lucknow Procurement Center",
            "procurement_date": "04 Sep 2026",
            "token": "KF-1042",
            "payment_method": "Direct Bank Transfer",
            "transaction_id": "Pending (Processing in Gateway)",
            "account_number": "XXXX-XXXX-4819",
            "ifsc_code": "SBIN0004819",
            "bank_name": "State Bank of India",
            "receipt_available": False,
            "timeline": [
                {"label": "Procurement Completed", "timestamp": "04 Sep 2026, 11:30 AM", "state": "done"},
                {"label": "Amount Calculated", "timestamp": "04 Sep 2026, 12:00 PM", "state": "done"},
                {"label": "Payment Initiated", "timestamp": "04 Sep 2026, 02:15 PM", "state": "done"},
                {"label": "Payment Processing", "timestamp": "04 Sep 2026, 03:00 PM", "state": "current"},
                {"label": "Payment Completed", "timestamp": "Expected 05 Sep 2026", "state": "pending"},
            ],
        },
        2: {
            "id": 2,
            "crop": "Rice",
            "registered_qty": "30.0 Quintals",
            "final_qty": "30.0 Quintal",
            "quality_grade": "Grade A",
            "rate": "₹616.66 / Quintal",
            "amount": "₹18,500",
            "status": "Completed",
            "status_code": "COMPLETED",
            "badge_color": "green",
            "expected_date": "28 Aug 2026",
            "procurement_center": "Gomti Procurement Hub",
            "procurement_date": "28 Aug 2026",
            "token": "KF-0982",
            "payment_method": "Direct Bank Transfer",
            "transaction_id": "TXN-849204812",
            "account_number": "XXXX-XXXX-4819",
            "ifsc_code": "SBIN0004819",
            "bank_name": "State Bank of India",
            "receipt_available": True,
            "timeline": [
                {"label": "Procurement Completed", "timestamp": "28 Aug 2026, 10:00 AM", "state": "done"},
                {"label": "Amount Calculated", "timestamp": "28 Aug 2026, 10:30 AM", "state": "done"},
                {"label": "Payment Initiated", "timestamp": "28 Aug 2026, 11:00 AM", "state": "done"},
                {"label": "Payment Processing", "timestamp": "28 Aug 2026, 11:30 AM", "state": "done"},
                {"label": "Payment Completed", "timestamp": "28 Aug 2026, 01:45 PM", "state": "done"},
            ],
        },
        3: {
            "id": 3,
            "crop": "Wheat",
            "registered_qty": "25.0 Quintals",
            "final_qty": "25.0 Quintal",
            "quality_grade": "Grade A",
            "rate": "₹600.00 / Quintal",
            "amount": "₹15,000",
            "status": "Completed",
            "status_code": "COMPLETED",
            "badge_color": "green",
            "expected_date": "15 Aug 2026",
            "procurement_center": "Lucknow Procurement Center",
            "procurement_date": "15 Aug 2026",
            "token": "KF-0871",
            "payment_method": "Direct Bank Transfer",
            "transaction_id": "TXN-739102948",
            "account_number": "XXXX-XXXX-4819",
            "ifsc_code": "SBIN0004819",
            "bank_name": "State Bank of India",
            "receipt_available": True,
            "timeline": [
                {"label": "Procurement Completed", "timestamp": "15 Aug 2026, 09:30 AM", "state": "done"},
                {"label": "Amount Calculated", "timestamp": "15 Aug 2026, 10:00 AM", "state": "done"},
                {"label": "Payment Initiated", "timestamp": "15 Aug 2026, 10:45 AM", "state": "done"},
                {"label": "Payment Processing", "timestamp": "15 Aug 2026, 11:15 AM", "state": "done"},
                {"label": "Payment Completed", "timestamp": "15 Aug 2026, 02:00 PM", "state": "done"},
            ],
        },
        4: {
            "id": 4,
            "crop": "Pulses",
            "registered_qty": "18.0 Quintals",
            "final_qty": "18.0 Quintal",
            "quality_grade": "Grade A+",
            "rate": "₹1,500.00 / Quintal",
            "amount": "₹27,000",
            "status": "Completed",
            "status_code": "COMPLETED",
            "badge_color": "green",
            "expected_date": "02 Aug 2026",
            "procurement_center": "Center A",
            "procurement_date": "02 Aug 2026",
            "token": "KF-0722",
            "payment_method": "Direct Bank Transfer",
            "transaction_id": "TXN-628104819",
            "account_number": "XXXX-XXXX-4819",
            "ifsc_code": "SBIN0004819",
            "bank_name": "State Bank of India",
            "receipt_available": True,
            "timeline": [
                {"label": "Procurement Completed", "timestamp": "02 Aug 2026, 09:15 AM", "state": "done"},
                {"label": "Amount Calculated", "timestamp": "02 Aug 2026, 09:45 AM", "state": "done"},
                {"label": "Payment Initiated", "timestamp": "02 Aug 2026, 10:30 AM", "state": "done"},
                {"label": "Payment Processing", "timestamp": "02 Aug 2026, 11:00 AM", "state": "done"},
                {"label": "Payment Completed", "timestamp": "02 Aug 2026, 01:15 PM", "state": "done"},
            ],
        },
        5: {
            "id": 5,
            "crop": "Mustard",
            "registered_qty": "10.0 Quintals",
            "final_qty": "10.0 Quintal",
            "quality_grade": "Grade B",
            "rate": "₹1,200.00 / Quintal",
            "amount": "₹12,000",
            "status": "Failed",
            "status_code": "FAILED",
            "badge_color": "red",
            "expected_date": "20 Jul 2026",
            "procurement_center": "Lucknow Procurement Center",
            "procurement_date": "20 Jul 2026",
            "token": "KF-0591",
            "payment_method": "Direct Bank Transfer",
            "transaction_id": "FAILED-BANK-MISMATCH",
            "account_number": "XXXX-XXXX-4819",
            "ifsc_code": "SBIN0004819",
            "bank_name": "State Bank of India",
            "receipt_available": False,
            "timeline": [
                {"label": "Procurement Completed", "timestamp": "20 Jul 2026, 10:00 AM", "state": "done"},
                {"label": "Amount Calculated", "timestamp": "20 Jul 2026, 10:30 AM", "state": "done"},
                {"label": "Payment Initiated", "timestamp": "20 Jul 2026, 11:00 AM", "state": "done"},
                {"label": "Payment Failed (Bank IFSC verification failed)", "timestamp": "20 Jul 2026, 11:15 AM", "state": "failed"},
            ],
        },
    }

    item = all_payments.get(payment_id, all_payments[1])

    return render(
        request,
        "payments/detail.html",
        {
            "farmer": request.user,
            "profile": profile,
            "payment": item,
        },
    )
