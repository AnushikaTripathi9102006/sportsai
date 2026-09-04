from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from produce.models import Produce


@login_required
def procurement_status(request):
    profile = getattr(request.user, "profile", None)

    # Fetch farmer's active produce
    produce_list = Produce.objects.filter(farmer=request.user).order_by("-created_at")
    active_produce = produce_list.filter(status="REQUESTED").first() or produce_list.first()

    # Stage switcher via query parameter for testing/demoing all state transitions
    selected_stage = request.GET.get("stage", "weighing").lower()

    valid_stages = ["verification", "quality", "weighing", "completed"]
    if selected_stage not in valid_stages:
        selected_stage = "weighing"

    stage_display_map = {
        "verification": "Verification in Progress",
        "quality": "Quality Inspection in Progress",
        "weighing": "Weighing in Progress",
        "completed": "Procurement Confirmed",
    }

    # Dynamic values based on active produce or defaults
    crop_name = active_produce.crop_name if active_produce else "Wheat"
    registered_qty = float(active_produce.quantity) if active_produce else 50.0
    actual_qty = round(registered_qty - 1.3, 2) if selected_stage in ["weighing", "completed"] else None
    diff_qty = round(actual_qty - registered_qty, 2) if actual_qty else None

    rate_per_quintal = 2275.00
    total_amount = round(actual_qty * rate_per_quintal, 2) if actual_qty else round(registered_qty * rate_per_quintal, 2)

    procurement_data = {
        "crop_name": crop_name,
        "registered_qty": registered_qty,
        "actual_qty": actual_qty,
        "diff_qty": diff_qty,
        "unit": active_produce.get_unit_display() if active_produce else "Quintals",
        "center_name": "Lucknow Procurement Hub",
        "counter_number": "Counter 2",
        "token_number": f"A-1{active_produce.id:02d}" if active_produce else "A-104",
        "appointment_time": "12 September 2026, 10:30 AM",
        "current_stage": selected_stage,
        "stage_title": stage_display_map[selected_stage],
        "overall_status": "Procurement Completed" if selected_stage == "completed" else "Procurement in Progress",
        # Verification
        "verification_status": "Completed" if selected_stage in ["quality", "weighing", "completed"] else "In Progress",
        "verified_by": "Officer R. Sharma",
        # Quality Check
        "quality_status": "Passed" if selected_stage in ["weighing", "completed"] else ("In Progress" if selected_stage == "quality" else "Pending"),
        "quality_grade": "Grade A",
        "moisture_content": "11.5%",
        "officer_remarks": "Produce meets all fair market procurement quality standards.",
        # Financials
        "rate_per_quintal": rate_per_quintal,
        "total_amount": total_amount,
        "payment_status": "Completed" if selected_stage == "completed" else "Processing",
    }

    procurement_history = [
        {"date": "28 Aug 2026", "crop": "Wheat", "quantity": "45.0 Quintals", "center": "Lucknow Hub", "amount": "₹102,375.00", "status": "Completed"},
        {"date": "18 Aug 2026", "crop": "Rice", "quantity": "30.0 Quintals", "center": "Gomti Center", "amount": "₹65,400.00", "status": "Completed"},
        {"date": "10 Aug 2026", "crop": "Pulses", "quantity": "20.0 Quintals", "center": "Center A", "amount": "₹48,000.00", "status": "Completed"},
    ]

    return render(
        request,
        "procurement_status/status.html",
        {
            "farmer": request.user,
            "profile": profile,
            "active_produce": active_produce,
            "procurement": procurement_data,
            "procurement_history": procurement_history,
            "selected_stage": selected_stage,
        },
    )


@login_required
def procurement_detail(request):
    profile = getattr(request.user, "profile", None)

    produce_list = Produce.objects.filter(farmer=request.user).order_by("-created_at")
    active_produce = produce_list.filter(status="REQUESTED").first() or produce_list.first()
    selected_stage = request.GET.get("stage", "weighing").lower()

    registered_qty = float(active_produce.quantity) if active_produce else 50.0
    actual_qty = round(registered_qty - 1.3, 2)
    rate_per_quintal = 2275.00
    total_amount = round(actual_qty * rate_per_quintal, 2)

    procurement_data = {
        "crop_name": active_produce.crop_name if active_produce else "Wheat",
        "registered_qty": registered_qty,
        "actual_qty": actual_qty,
        "diff_qty": round(actual_qty - registered_qty, 2),
        "unit": active_produce.get_unit_display() if active_produce else "Quintals",
        "harvest_date": active_produce.harvest_date.strftime("%d %b %Y") if active_produce else "01 Sep 2026",
        "center_name": "Lucknow Procurement Hub",
        "counter_number": "Counter 2",
        "token_number": f"A-1{active_produce.id:02d}" if active_produce else "A-104",
        "appointment_time": "12 September 2026, 10:30 AM",
        "verified_by": "Officer R. Sharma",
        "quality_grade": "Grade A",
        "moisture_content": "11.5%",
        "officer_remarks": "Produce meets all fair market procurement quality standards.",
        "rate_per_quintal": rate_per_quintal,
        "total_amount": total_amount,
        "payment_status": "Processing",
    }

    timeline_items = [
        {"stage": "Produce Registered", "timestamp": "01 Sep 2026, 09:30 AM", "status": "done"},
        {"stage": "Appointment Confirmed", "timestamp": "10 Sep 2026, 02:15 PM", "status": "done"},
        {"stage": "Farmer Arrived", "timestamp": "12 Sep 2026, 10:20 AM", "status": "done"},
        {"stage": "Verification Completed", "timestamp": "12 Sep 2026, 10:45 AM", "status": "done"},
        {"stage": "Quality Inspection Passed", "timestamp": "12 Sep 2026, 11:10 AM", "status": "done"},
        {"stage": "Weighing Recorded (48.7 Q)", "timestamp": "12 Sep 2026, 11:35 AM", "status": "current"},
        {"stage": "Procurement Confirmed", "timestamp": "Pending", "status": "pending"},
        {"stage": "Payment Processing", "timestamp": "Pending", "status": "pending"},
        {"stage": "Payment Completed", "timestamp": "Pending", "status": "pending"},
    ]

    return render(
        request,
        "procurement_status/detail.html",
        {
            "farmer": request.user,
            "profile": profile,
            "active_produce": active_produce,
            "procurement": procurement_data,
            "timeline": timeline_items,
            "selected_stage": selected_stage,
        },
    )
