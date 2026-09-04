from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from produce.models import Produce


@login_required
def payments(request):
    profile = getattr(request.user, "profile", None)

    # Overview Cards Mock Metrics (isolated & clear for easy API replacement)
    overview = {
        "total_earned": "₹84,500",
        "pending_amount": "₹12,000",
        "paid_amount": "₹72,500",
        "last_payment": "₹25,000",
        "last_payment_date": "28 Aug 2026",
    }

    # Latest / Current Payment in Progress
    current_payment = {
        "id": 1,
        "crop": "Wheat",
        "quantity": "45 Quintal",
        "rate": "₹2,666 / Quintal",
        "quality_grade": "Grade A",
        "amount": "₹12,000",
        "status_code": "PROCESSING",
        "status_label": "Processing",
        "procurement_date": "04 Sep 2026",
        "expected_date": "05 Sep 2026",
        "token_number": "KF-1042",
        "center_name": "Lucknow Procurement Center",
        "payment_method": "Direct Bank Transfer",
        "transaction_id": "Pending",
        "stepper": [
            {"label": "Amount Calculated", "state": "done"},
            {"label": "Payment Initiated", "state": "done"},
            {"label": "Processing", "state": "current"},
            {"label": "Payment Completed", "state": "pending"},
        ],
    }

    # Smart Payment Update (with preview query param ?delay=1)
    is_delayed = request.GET.get("delay", "0") == "1"
    smart_update = {
        "is_delayed": is_delayed,
        "title": "⚠️ PAYMENT DELAY" if is_delayed else "🤖 PAYMENT UPDATE",
        "message": (
            "Your ₹12,000 payment for Wheat is taking slightly longer than expected due to bank network queue. "
            "KisanFlow is monitoring the payment status automatically. You don't need to take any action right now."
            if is_delayed
            else "Your payment of ₹12,000 is currently processing. Based on the current payment status, "
            "it is expected to reach your bank account by 05 Sep 2026."
        ),
    }

    # Payment History Data
    history_records = [
        {
            "id": 1,
            "date": "04 Sep 2026",
            "crop": "Wheat",
            "quantity": "45 Q",
            "amount": "₹12,000",
            "status": "Processing",
            "status_code": "PROCESSING",
            "badge_color": "yellow",
            "receipt_available": False,
        },
        {
            "id": 2,
            "date": "28 Aug 2026",
            "crop": "Rice",
            "quantity": "30 Q",
            "amount": "₹18,500",
            "status": "Completed",
            "status_code": "COMPLETED",
            "badge_color": "green",
            "receipt_available": True,
        },
        {
            "id": 3,
            "date": "15 Aug 2026",
            "crop": "Wheat",
            "quantity": "25 Q",
            "amount": "₹15,000",
            "status": "Completed",
            "status_code": "COMPLETED",
            "badge_color": "green",
            "receipt_available": True,
        },
        {
            "id": 4,
            "date": "02 Aug 2026",
            "crop": "Pulses",
            "quantity": "18 Q",
            "amount": "₹27,000",
            "status": "Completed",
            "status_code": "COMPLETED",
            "badge_color": "green",
            "receipt_available": True,
        },
        {
            "id": 5,
            "date": "20 Jul 2026",
            "crop": "Mustard",
            "quantity": "10 Q",
            "amount": "₹12,000",
            "status": "Failed",
            "status_code": "FAILED",
            "badge_color": "red",
            "receipt_available": False,
        },
    ]

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
