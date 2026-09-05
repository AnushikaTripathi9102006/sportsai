from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models, transaction
from produce.models import Produce
from .models import ProcurementCenter, ProcurementRecord
from produce.forms import UP_DISTRICTS
from .permissions import officer_required
from .forms import (
    GateEntryForm,
    QualityCheckForm,
    WeighingForm,
    AcceptanceForm,
    BillGenerationForm,
    PaymentInitiationForm,
    PaymentReceivedForm,
)
from .services import (
    sync_all_farmer_procurements,
    transition_procurement_stage,
    perform_gate_entry,
    perform_quality_check,
    perform_weighing,
    perform_acceptance,
    perform_bill_generation,
    perform_payment_initiation,
    perform_payment_received,
)



@login_required
def centers(request):
    profile = getattr(request.user, "profile", None)

    # Fetch farmer's latest registered produce
    produce_list = Produce.objects.filter(farmer=request.user).order_by("-created_at")
    active_produce = produce_list.first()

    # Determine target district from GET search or produce district or default
    selected_district = request.GET.get("district", "").strip()
    search_query = request.GET.get("search", "").strip()
    selected_queue = request.GET.get("queue", "").strip().upper()

    if not selected_district and active_produce:
        selected_district = getattr(active_produce, "district", "Lucknow")
    if not selected_district:
        selected_district = "Lucknow"

    all_centers = ProcurementCenter.objects.filter(is_active=True)

    # Filter by search query
    filtered_centers = all_centers
    if search_query:
        filtered_centers = filtered_centers.filter(name__icontains=search_query)

    # Filter by queue status
    if selected_queue in ["LOW", "MEDIUM", "HIGH"]:
        filtered_centers = filtered_centers.filter(queue_status=selected_queue)

    # Priority matching by district
    same_district_centers = filtered_centers.filter(district__iexact=selected_district)
    other_district_centers = filtered_centers.exclude(district__iexact=selected_district)

    nearby_centers = list(same_district_centers) + list(other_district_centers)

    recommended_center = same_district_centers.first() or filtered_centers.first() or all_centers.first()

    up_districts_list = [d[0] for d in UP_DISTRICTS]

    return render(
        request,
        "procurement/centers.html",
        {
            "farmer": request.user,
            "profile": profile,
            "active_produce": active_produce,
            "recommended_center": recommended_center,
            "nearby_centers": nearby_centers,
            "selected_district": selected_district,
            "search_query": search_query,
            "selected_queue": selected_queue,
            "up_districts": up_districts_list,
        },
    )


@login_required
def center_detail(request):
    return render(request, "procurement/center_detail.html")


@login_required
def confirm_center(request):
    return render(request, "procurement/confirm_center.html")


@login_required
def status(request):
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
        "procurement/status.html",
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
def status_detail(request):
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
        "procurement/status_detail.html",
        {
            "farmer": request.user,
            "profile": profile,
            "active_produce": active_produce,
            "procurement": procurement_data,
            "timeline": timeline_items,
            "selected_stage": selected_stage,
        },
    )


# ==============================================================================
# PROCUREMENT OFFICER WORKFLOW VIEWS
# ==============================================================================

def _get_officer_records(center):
    if center:
        return ProcurementRecord.objects.filter(
            models.Q(
                models.Q(center=center),
                models.Q(center__district__iexact=center.district),
                models.Q(produce__district__iexact=center.district),
                models.Q(center__isnull=True),
                _connector=models.Q.OR,
            )
        ).distinct()
    return ProcurementRecord.objects.all()


@login_required
@officer_required
def officer_appointments(request):
    sync_all_farmer_procurements()
    profile = request.user.profile
    center = profile.assigned_center

    if request.method == "POST":
        record_id = request.POST.get("record_id")
        appointment_date = request.POST.get("appointment_date", "").strip()
        if record_id and appointment_date:
            rec = get_object_or_404(ProcurementRecord, pk=record_id)
            rec.appointment_date = appointment_date
            if rec.current_stage == "REGISTRATION":
                rec.current_stage = "APPOINTMENT"
            rec.save()
            messages.success(request, f"Successfully updated appointment slot for {rec.farmer.get_full_name() or rec.farmer.username} to '{appointment_date}'.")
            return redirect("procurement:officer_appointments")

    records = _get_officer_records(center)

    search_query = request.GET.get("search", "").strip()
    selected_stage = request.GET.get("stage", "").strip()

    if search_query:
        records = records.filter(
            models.Q(
                models.Q(farmer__username__icontains=search_query),
                models.Q(farmer__first_name__icontains=search_query),
                models.Q(farmer__last_name__icontains=search_query),
                models.Q(token_number__icontains=search_query),
                models.Q(crop_name__icontains=search_query),
                _connector=models.Q.OR,
            )
        )

    if selected_stage:
        records = records.filter(current_stage=selected_stage)

    stage_choices = ProcurementRecord.STAGE_CHOICES

    return render(
        request,
        "procurement/officer_appointments.html",
        {
            "officer": request.user,
            "profile": profile,
            "center": center,
            "records": records,
            "search_query": search_query,
            "selected_stage": selected_stage,
            "stage_choices": stage_choices,
            "total_appointments": records.count(),
        },
    )


@login_required
@officer_required
def officer_gate_entry(request, pk=None):
    sync_all_farmer_procurements()
    profile = request.user.profile
    center = profile.assigned_center

    target_pk = pk or request.POST.get("record_id") or request.GET.get("record_id")

    if request.method == "POST":
        if target_pk:
            record = get_object_or_404(ProcurementRecord, pk=target_pk)
            vehicle_number = request.POST.get("vehicle_number", "").strip()
            notes = request.POST.get("notes", "").strip()

            if vehicle_number:
                record.vehicle_number = vehicle_number
                record.save()

            try:
                perform_gate_entry(request.user, record, vehicle_number=vehicle_number, notes=notes)
                messages.success(request, f"Gate Entry confirmed for Farmer {record.farmer.get_full_name() or record.farmer.username} (Token: #{record.token_number}).")
            except Exception as e:
                messages.error(request, str(e))
            return redirect("procurement:officer_gate_entry")

    base_records = _get_officer_records(center)
    pending_records = base_records.filter(current_stage__in=["REGISTRATION", "APPOINTMENT"])
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else pending_records.first()

    form = GateEntryForm()

    return render(
        request,
        "procurement/gate_entry.html",
        {
            "officer": request.user,
            "profile": profile,
            "center": center,
            "pending_records": pending_records,
            "selected_record": selected_record,
            "form": form,
        },
    )


@login_required
@officer_required
def officer_queue(request):
    sync_all_farmer_procurements()
    profile = request.user.profile
    center = profile.assigned_center

    base_records = _get_officer_records(center)
    active_records = base_records.filter(
        current_stage__in=["GATE_ENTRY", "QUALITY_CHECK", "WEIGHING", "ACCEPTANCE", "BILL_GENERATED", "PAYMENT_INITIATED"]
    )

    queue_counts = {
        "gate_entry": base_records.filter(current_stage="GATE_ENTRY").count(),
        "quality_check": base_records.filter(current_stage="QUALITY_CHECK").count(),
        "weighing": base_records.filter(current_stage="WEIGHING").count(),
        "acceptance": base_records.filter(current_stage="ACCEPTANCE").count(),
        "bill_generated": base_records.filter(current_stage="BILL_GENERATED").count(),
        "payment_initiated": base_records.filter(current_stage="PAYMENT_INITIATED").count(),
    }

    return render(
        request,
        "procurement/officer_queue.html",
        {
            "officer": request.user,
            "profile": profile,
            "center": center,
            "active_records": active_records,
            "queue_counts": queue_counts,
        },
    )


@login_required
@officer_required
def officer_quality_check(request, pk=None):
    sync_all_farmer_procurements()
    profile = request.user.profile
    center = profile.assigned_center

    target_pk = pk or request.POST.get("record_id") or request.GET.get("record_id")

    if request.method == "POST":
        if target_pk:
            record = get_object_or_404(ProcurementRecord, pk=target_pk)
            is_passed_val = request.POST.get("is_passed", "True")
            is_passed = is_passed_val in ["True", "true", "1", True]
            result = "PASSED" if is_passed else "REJECTED"
            quality_grade = request.POST.get("quality_grade", "GRADE_A")
            moisture = request.POST.get("moisture_percentage", 11.50)
            foreign = request.POST.get("foreign_matter_percentage", 1.00)
            remarks = request.POST.get("remarks", "").strip()

            try:
                perform_quality_check(
                    officer=request.user,
                    record=record,
                    result=result,
                    quality_grade=quality_grade,
                    moisture_percentage=float(moisture),
                    foreign_matter_percentage=float(foreign),
                    remarks=remarks,
                )
                messages.success(request, f"Quality Assessment ({result}) saved for Farmer {record.farmer.get_full_name() or record.farmer.username}.")
            except Exception as e:
                messages.error(request, str(e))
            return redirect("procurement:officer_quality_check")

    base_records = _get_officer_records(center)
    pending_records = base_records.filter(current_stage="GATE_ENTRY")
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else pending_records.first()

    form = QualityCheckForm()

    return render(
        request,
        "procurement/quality_check.html",
        {
            "officer": request.user,
            "profile": profile,
            "center": center,
            "pending_records": pending_records,
            "selected_record": selected_record,
            "form": form,
        },
    )


@login_required
@officer_required
def officer_weighing(request, pk=None):
    sync_all_farmer_procurements()
    profile = request.user.profile
    center = profile.assigned_center

    target_pk = pk or request.POST.get("record_id") or request.GET.get("record_id")

    if request.method == "POST":
        if target_pk:
            record = get_object_or_404(ProcurementRecord, pk=target_pk)
            gross = request.POST.get("gross_weight", 0)
            tare = request.POST.get("tare_weight", 0)
            remarks = request.POST.get("remarks", "").strip()

            try:
                perform_weighing(request.user, record, gross_weight=float(gross), tare_weight=float(tare), remarks=remarks)
                messages.success(request, f"Weighing scale recorded for {record.farmer.username}. Net Weight: {record.actual_quantity} Quintals.")
            except Exception as e:
                messages.error(request, str(e))
            return redirect("procurement:officer_weighing")

    base_records = _get_officer_records(center)
    pending_records = base_records.filter(current_stage="QUALITY_CHECK")
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else pending_records.first()

    form = WeighingForm()

    return render(
        request,
        "procurement/weighing.html",
        {
            "officer": request.user,
            "profile": profile,
            "center": center,
            "pending_records": pending_records,
            "selected_record": selected_record,
            "form": form,
        },
    )


@login_required
@officer_required
def officer_acceptance(request, pk=None):
    sync_all_farmer_procurements()
    profile = request.user.profile
    center = profile.assigned_center

    target_pk = pk or request.POST.get("record_id") or request.GET.get("record_id")

    if request.method == "POST":
        if target_pk:
            record = get_object_or_404(ProcurementRecord, pk=target_pk)
            decision = request.POST.get("decision", "ACCEPT")
            remarks = request.POST.get("remarks", "").strip()

            try:
                perform_acceptance(request.user, record, decision=decision, rejection_reason=remarks)
                if decision == "ACCEPT":
                    messages.success(request, f"Procurement ACCEPTED for Farmer {record.farmer.get_full_name() or record.farmer.username}. Moving to Billing section.")
                    return redirect("procurement:officer_bills")
                else:
                    messages.warning(request, f"Procurement REJECTED for Farmer {record.farmer.get_full_name() or record.farmer.username}.")
            except Exception as e:
                messages.error(request, str(e))
            return redirect("procurement:officer_acceptance")

    base_records = _get_officer_records(center)
    pending_records = base_records.filter(current_stage="WEIGHING")
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else pending_records.first()

    form = AcceptanceForm()

    return render(
        request,
        "procurement/acceptance.html",
        {
            "officer": request.user,
            "profile": profile,
            "center": center,
            "pending_records": pending_records,
            "selected_record": selected_record,
            "form": form,
        },
    )


@login_required
@officer_required
def officer_bills(request, pk=None):
    sync_all_farmer_procurements()
    profile = request.user.profile
    center = profile.assigned_center

    target_pk = pk or request.POST.get("record_id") or request.GET.get("record_id")

    if request.method == "POST":
        if target_pk:
            record = get_object_or_404(ProcurementRecord, pk=target_pk)
            rate = request.POST.get("rate_per_quintal", 2275.00)
            deductions = request.POST.get("deductions", 0.00)
            remarks = request.POST.get("remarks", "").strip()

            try:
                bill = perform_bill_generation(request.user, record, rate_per_quintal=float(rate), deductions=float(deductions))
                messages.success(request, f"Bill #{bill.bill_number} generated successfully for ₹{bill.net_amount}.")
            except Exception as e:
                messages.error(request, str(e))
            return redirect("procurement:officer_bills")

    base_records = _get_officer_records(center)
    pending_records = base_records.filter(current_stage="ACCEPTANCE")
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else pending_records.first()

    form = BillGenerationForm(initial={"rate_per_quintal": 2275.00, "deductions": 0.00})

    return render(
        request,
        "procurement/bills.html",
        {
            "officer": request.user,
            "profile": profile,
            "center": center,
            "pending_records": pending_records,
            "selected_record": selected_record,
            "form": form,
        },
    )


@login_required
@officer_required
def officer_payments(request, pk=None):
    sync_all_farmer_procurements()
    profile = request.user.profile
    center = profile.assigned_center

    target_pk = pk or request.POST.get("record_id") or request.GET.get("record_id")

    if request.method == "POST":
        if target_pk:
            record = get_object_or_404(ProcurementRecord, pk=target_pk)
            action_type = request.POST.get("action_type", "initiate")
            txn_ref = request.POST.get("transaction_reference", "").strip()
            payment_mode = request.POST.get("payment_mode", "Bank Transfer / DBT")
            notes = request.POST.get("notes", "").strip()
            confirmation_notes = request.POST.get("confirmation_notes", "").strip()

            try:
                if action_type == "initiate":
                    perform_payment_initiation(request.user, record, transaction_reference=txn_ref)
                    messages.success(request, f"Payment initiated for Farmer {record.farmer.get_full_name() or record.farmer.username}. Ref: {txn_ref}.")
                elif action_type in ["confirm", "receive"]:
                    perform_payment_received(request.user, record)
                    messages.success(request, f"Payment CONFIRMED & Procurement COMPLETED for Farmer {record.farmer.get_full_name() or record.farmer.username}!")
            except Exception as e:
                messages.error(request, str(e))
            return redirect("procurement:officer_payments")

    base_records = _get_officer_records(center)
    pending_records = base_records.filter(current_stage__in=["BILL_GENERATED", "PAYMENT_INITIATED"])
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else pending_records.first()

    initiate_form = PaymentInitiationForm()
    receive_form = PaymentReceivedForm()

    return render(
        request,
        "procurement/officer_payments.html",
        {
            "officer": request.user,
            "profile": profile,
            "center": center,
            "pending_records": pending_records,
            "selected_record": selected_record,
            "initiate_form": initiate_form,
            "receive_form": receive_form,
        },
    )


@login_required
@officer_required
def officer_history(request):
    sync_all_farmer_procurements()
    profile = request.user.profile
    center = profile.assigned_center

    records = _get_officer_records(center)

    search_query = request.GET.get("search", "").strip()
    selected_stage = request.GET.get("stage", "").strip()
    selected_crop = request.GET.get("crop", "").strip()

    if search_query:
        records = records.filter(
            models.Q(
                models.Q(farmer__username__icontains=search_query),
                models.Q(farmer__first_name__icontains=search_query),
                models.Q(farmer__last_name__icontains=search_query),
                models.Q(crop_name__icontains=search_query),
                models.Q(token_number__icontains=search_query),
                _connector=models.Q.OR,
            )
        )

    if selected_stage:
        records = records.filter(current_stage=selected_stage)

    if selected_crop:
        records = records.filter(crop_name__iexact=selected_crop)

    crops = list(ProcurementRecord.objects.values_list("crop_name", flat=True).distinct())

    return render(
        request,
        "procurement/officer_history.html",
        {
            "officer": request.user,
            "profile": profile,
            "center": center,
            "records": records,
            "search_query": search_query,
            "selected_stage": selected_stage,
            "selected_crop": selected_crop,
            "crops": crops,
        },
    )

