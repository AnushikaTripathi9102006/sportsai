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



from .recommendation_engine import get_recommended_centers


@login_required
def centers(request):
    profile = getattr(request.user, "profile", None)

    # Fetch farmer's latest registered produce or produce requested via query param
    produce_list = Produce.objects.filter(farmer=request.user).order_by("-created_at")
    produce_id = request.GET.get("produce_id")
    active_produce = None
    if produce_id:
        active_produce = produce_list.filter(pk=produce_id).first()
    if not active_produce:
        active_produce = produce_list.first()

    # Determine target district
    selected_district = request.GET.get("district", "").strip()
    search_query = request.GET.get("search", "").strip()
    selected_queue = request.GET.get("queue", "").strip().upper()

    if not selected_district and active_produce:
        selected_district = getattr(active_produce, "district", "Lucknow")
    if not selected_district:
        selected_district = "Lucknow"

    # Use Intelligent Recommendation Engine
    top_recommendation, ranked_centers = get_recommended_centers(
        produce=active_produce,
        farmer=request.user,
        target_district=selected_district,
    )

    # Apply search and queue filters if provided
    filtered_centers = ranked_centers
    if search_query:
        filtered_centers = [c for c in filtered_centers if search_query.lower() in c.name.lower()]
    if selected_queue in ["LOW", "MEDIUM", "HIGH"]:
        filtered_centers = [c for c in filtered_centers if (c.queue_status or "LOW").upper() == selected_queue]

    up_districts_list = [d[0] for d in UP_DISTRICTS]

    return render(
        request,
        "procurement/centers.html",
        {
            "farmer": request.user,
            "profile": profile,
            "active_produce": active_produce,
            "recommended_center": top_recommendation,
            "ranked_centers": filtered_centers,
            "nearby_centers": filtered_centers,
            "selected_district": selected_district,
            "search_query": search_query,
            "selected_queue": selected_queue,
            "up_districts": up_districts_list,
        },
    )


@login_required
def select_center(request):
    """
    Farmer Explicit Center Selection Endpoint.
    Saves the selected procurement center against the farmer's procurement record.
    """
    if request.method != "POST":
        return redirect("procurement:centers")

    produce_id = request.POST.get("produce_id")
    center_id = request.POST.get("center_id")

    if not produce_id or not center_id:
        messages.error(request, "Please select a valid produce batch and procurement center.")
        return redirect("procurement:centers")

    produce = get_object_or_404(Produce, pk=produce_id, farmer=request.user)
    center = get_object_or_404(ProcurementCenter, pk=center_id, is_active=True)

    # Backend Validation: Ensure center handles the crop
    from .recommendation_engine import is_crop_handled
    if not is_crop_handled(produce.crop_name, center.crops_handled):
        messages.error(request, f"Center '{center.name}' does not handle procurement for crop '{produce.crop_name}'.")
        return redirect(f"/procurement/centers/?produce_id={produce.id}")

    with transaction.atomic():
        rec, created = ProcurementRecord.objects.get_or_create(
            produce=produce,
            farmer=request.user,
            defaults={
                "crop_name": produce.crop_name,
                "registered_quantity": produce.quantity,
                "unit": produce.get_unit_display(),
                "center": center,
                "center_name": center.name,
                "current_stage": "REGISTRATION",
            },
        )
        if not created:
            rec.center = center
            rec.center_name = center.name
            rec.save()

        if produce.status == "AVAILABLE":
            produce.status = "REQUESTED"
            produce.save()

        from notifications.services import notify_farmer
        notify_farmer(
            farmer_user=request.user,
            title="📍 Procurement Center Selected",
            message=f"Your procurement request for {produce.crop_name} has been registered at {center.name}.",
            notification_type="CENTER_ASSIGNED",
            target_url=f"/appointments/book/?produce_id={produce.id}&center_id={center.id}",
            related_object=center,
            event_key=f"center_select_{produce.id}_{center.id}",
        )

    messages.success(request, f"Procurement center '{center.name}' selected! Now select your appointment date and time slot.")
    return redirect(f"/appointments/book/?produce_id={produce.id}&center_id={center.id}")


@login_required
def center_detail(request):
    return render(request, "procurement/center_detail.html")


@login_required
def confirm_center(request):
    return render(request, "procurement/confirm_center.html")


STAGE_RANKS = {
    "AVAILABLE": 0,
    "REQUESTED": 1,
    "REGISTRATION": 1,
    "APPOINTMENT": 2,
    "GATE_ENTRY": 3,
    "QUALITY_CHECK": 4,
    "WEIGHING": 5,
    "ACCEPTANCE": 6,
    "BILL_GENERATED": 7,
    "PAYMENT_INITIATED": 8,
    "PAYMENT_RECEIVED": 9,
    "COMPLETED": 10,
    "REJECTED": -1,
    "CANCELLED": -1,
}

def _build_produce_status_dict(produce, farmer):
    from appointments.models import Appointment
    from tokens.models import Token

    rec = ProcurementRecord.objects.filter(produce=produce, farmer=farmer).first()
    appt = Appointment.objects.filter(produce=produce, farmer=farmer).first() if not rec else None
    tok = Token.objects.filter(produce=produce, farmer=farmer).first() if not rec else None

    registered_qty = float(produce.quantity)
    unit = produce.get_unit_display()

    if rec:
        stage = rec.current_stage
        stage_rank = STAGE_RANKS.get(stage, 1)
        stage_display = rec.get_current_stage_display()
        center_name = rec.center.name if rec.center else (rec.center_name or "Procurement Center")
        token_number = f"#{rec.token_number}" if rec.token_number else "Pending"
        appointment_time = rec.appointment_date or "Slot Assigned"
        
        actual_qty = float(rec.actual_quantity) if rec.actual_quantity is not None else None
        diff_qty = round(actual_qty - registered_qty, 2) if actual_qty is not None else None
        
        verified_by = rec.verified_by or "Procurement Officer"
        verification_status = "Completed" if stage_rank >= 3 else ("In Progress" if stage_rank == 2 else "Pending")

        quality_assessment = getattr(rec, "quality_assessment", None)
        if quality_assessment:
            quality_status = quality_assessment.get_result_display()
            quality_grade = quality_assessment.get_quality_grade_display()
            moisture_content = f"{quality_assessment.moisture_percentage}%"
            officer_remarks = quality_assessment.remarks or rec.officer_remarks or "Quality inspection completed."
        else:
            quality_status = rec.quality_status
            quality_grade = rec.quality_grade
            moisture_content = rec.moisture_content
            officer_remarks = rec.officer_remarks or ("Quality inspection pending." if stage_rank < 4 else "In progress")

        bill = getattr(rec, "bill", None)
        if bill:
            rate_per_quintal = float(bill.rate_per_quintal)
            total_amount = float(bill.net_amount)
        else:
            rate_per_quintal = float(rec.rate_per_unit)
            total_amount = float(rec.total_amount) if rec.total_amount else round((actual_qty or registered_qty) * rate_per_quintal, 2)

        payment_record = getattr(rec, "payment_record", None)
        if payment_record:
            payment_status = payment_record.get_payment_status_display()
        else:
            payment_status = rec.payment_status

        overall_status = f"Status: {stage_display}"
        if stage == "COMPLETED":
            overall_status = "Procurement Completed ✅"
        elif stage == "REJECTED":
            overall_status = "Procurement Rejected ❌"

    elif appt:
        stage = "APPOINTMENT"
        stage_rank = 2
        stage_display = "Appointment Confirmed"
        center_name = appt.procurement_center.name if appt.procurement_center else "Procurement Center"
        token_number = f"#{appt.token_number}" if appt.token_number else "Pending"
        appointment_time = f"{appt.appointment_date} ({appt.appointment_time_slot})"
        actual_qty = None
        diff_qty = None
        verified_by = "Procurement Officer"
        verification_status = "Pending"
        quality_status = "Pending"
        quality_grade = "Pending"
        moisture_content = "--"
        officer_remarks = "Awaiting arrival at center."
        rate_per_quintal = 2275.00
        total_amount = round(registered_qty * rate_per_quintal, 2)
        payment_status = "Pending"
        overall_status = "Appointment Confirmed 📅"

    elif tok:
        stage = "APPOINTMENT"
        stage_rank = 2
        stage_display = f"Token Issued (#{tok.token_number})"
        center_name = tok.procurement_center.name if tok.procurement_center else "Procurement Center"
        token_number = f"#{tok.token_number}"
        appointment_time = f"{tok.date}"
        actual_qty = None
        diff_qty = None
        verified_by = "Procurement Officer"
        verification_status = "Pending"
        quality_status = "Pending"
        quality_grade = "Pending"
        moisture_content = "--"
        officer_remarks = "Token generated."
        rate_per_quintal = 2275.00
        total_amount = round(registered_qty * rate_per_quintal, 2)
        payment_status = "Pending"
        overall_status = "Token Active 🎟️"

    elif produce.status == "REQUESTED":
        stage = "REQUESTED"
        stage_rank = 1
        stage_display = "Procurement Requested"
        center_name = "Awaiting Center Selection"
        token_number = "--"
        appointment_time = "--"
        actual_qty = None
        diff_qty = None
        verified_by = "Procurement Officer"
        verification_status = "Pending"
        quality_status = "Pending"
        quality_grade = "Pending"
        moisture_content = "--"
        officer_remarks = "Procurement requested. Please select a procurement center."
        rate_per_quintal = 2275.00
        total_amount = round(registered_qty * rate_per_quintal, 2)
        payment_status = "Pending"
        overall_status = "Procurement Requested 📦"

    else:
        stage = "AVAILABLE"
        stage_rank = 0
        stage_display = "Available / Not Requested"
        center_name = "--"
        token_number = "--"
        appointment_time = "--"
        actual_qty = None
        diff_qty = None
        verified_by = "--"
        verification_status = "Not Started"
        quality_status = "Not Started"
        quality_grade = "--"
        moisture_content = "--"
        officer_remarks = "Produce registered. Click 'Request Procurement' to select a center."
        rate_per_quintal = 2275.00
        total_amount = round(registered_qty * rate_per_quintal, 2)
        payment_status = "Not Started"
        overall_status = "Available for Procurement 🌾"

    return {
        "produce": produce,
        "id": produce.id,
        "crop_name": produce.crop_name,
        "registered_qty": registered_qty,
        "actual_qty": actual_qty,
        "diff_qty": diff_qty,
        "unit": unit,
        "status": produce.status,
        "harvest_date": produce.harvest_date,
        "center_name": center_name,
        "counter_number": rec.counter_number if rec else "Counter 1",
        "token_number": token_number,
        "appointment_time": appointment_time,
        "stage": stage,
        "stage_rank": stage_rank,
        "stage_title": stage_display,
        "overall_status": overall_status,
        "verification_status": verification_status,
        "verified_by": verified_by,
        "quality_status": quality_status,
        "quality_grade": quality_grade,
        "moisture_content": moisture_content,
        "officer_remarks": officer_remarks,
        "rate_per_quintal": rate_per_quintal,
        "total_amount": total_amount,
        "payment_status": payment_status,
        "procurement_record": rec,
    }


@login_required
def status(request):
    sync_all_farmer_procurements()
    profile = getattr(request.user, "profile", None)

    produce_list = Produce.objects.filter(farmer=request.user).order_by("-created_at")
    all_farmer_crops = [_build_produce_status_dict(p, request.user) for p in produce_list]

    target_produce_id = request.GET.get("produce_id")
    active_crop = None
    if target_produce_id:
        active_crop = next((c for c in all_farmer_crops if str(c["id"]) == str(target_produce_id)), None)
    if not active_crop:
        # Default to first crop in progress / requested, or first crop
        active_crop = next((c for c in all_farmer_crops if c["stage_rank"] > 0), None) or (all_farmer_crops[0] if all_farmer_crops else None)

    history_records = ProcurementRecord.objects.filter(farmer=request.user, current_stage="COMPLETED").order_by("-updated_at")
    procurement_history = [
        {
            "id": rec.id,
            "date": rec.updated_at.strftime("%d %b %Y"),
            "crop": rec.crop_name,
            "quantity": f"{rec.actual_quantity or rec.registered_quantity} {rec.unit}",
            "center": rec.center_display_name,
            "amount": f"₹{rec.bill.net_amount:,.2f}" if hasattr(rec, "bill") else f"₹{rec.total_amount:,.2f}",
            "status": "Completed",
        }
        for rec in history_records
    ]

    return render(
        request,
        "procurement/status.html",
        {
            "farmer": request.user,
            "profile": profile,
            "all_farmer_crops": all_farmer_crops,
            "active_crop": active_crop,
            "procurement": active_crop,
            "procurement_history": procurement_history,
            "total_crops_count": len(all_farmer_crops),
        },
    )


@login_required
def status_detail(request):
    sync_all_farmer_procurements()
    profile = getattr(request.user, "profile", None)

    produce_list = Produce.objects.filter(farmer=request.user).order_by("-created_at")
    all_farmer_crops = [_build_produce_status_dict(p, request.user) for p in produce_list]

    target_produce_id = request.GET.get("produce_id")
    active_crop = None
    if target_produce_id:
        active_crop = next((c for c in all_farmer_crops if str(c["id"]) == str(target_produce_id)), None)
    if not active_crop:
        active_crop = next((c for c in all_farmer_crops if c["stage_rank"] > 0), None) or (all_farmer_crops[0] if all_farmer_crops else None)

    timeline_items = []
    if active_crop:
        rank = active_crop["stage_rank"]
        rec = active_crop["procurement_record"]

        created_ts = produce_list.filter(id=active_crop["id"]).first().created_at.strftime("%d %b %Y, %I:%M %p") if produce_list.filter(id=active_crop["id"]).first() else "Registered"
        
        timeline_items = [
            {"stage": "Produce Registered", "timestamp": created_ts, "status": "done" if rank >= 1 else "current"},
            {"stage": "Appointment & Center Confirmed", "timestamp": active_crop["appointment_time"], "status": "done" if rank >= 2 else ("current" if rank == 1 else "pending")},
            {"stage": "Gate Entry & Arrival", "timestamp": rec.gate_entry_at.strftime("%d %b %Y, %I:%M %p") if (rec and rec.gate_entry_at) else "Pending", "status": "done" if rank >= 3 else ("current" if rank == 2 else "pending")},
            {"stage": "Identity & Produce Verification", "timestamp": f"Verified by {active_crop['verified_by']}" if rank >= 3 else "Pending", "status": "done" if rank >= 4 else ("current" if rank == 3 else "pending")},
            {"stage": "Quality Inspection Passed", "timestamp": f"Grade {active_crop['quality_grade']} ({active_crop['moisture_content']})" if rank >= 4 else "Pending", "status": "done" if rank >= 5 else ("current" if rank == 4 else "pending")},
            {"stage": "Weighing Scale Measured", "timestamp": f"{active_crop['actual_qty']} {active_crop['unit']}" if active_crop['actual_qty'] else "Pending", "status": "done" if rank >= 6 else ("current" if rank == 5 else "pending")},
            {"stage": "Final Batch Acceptance", "timestamp": "Approved by Officer" if rank >= 6 else "Pending", "status": "done" if rank >= 7 else ("current" if rank == 6 else "pending")},
            {"stage": "Bill Generated", "timestamp": f"₹{active_crop['total_amount']:,.2f}" if rank >= 7 else "Pending", "status": "done" if rank >= 8 else ("current" if rank == 7 else "pending")},
            {"stage": "Payment Disbursement & Completed", "timestamp": active_crop["payment_status"], "status": "done" if rank >= 9 else ("current" if rank == 8 else "pending")},
        ]

    return render(
        request,
        "procurement/status_detail.html",
        {
            "farmer": request.user,
            "profile": profile,
            "active_produce": produce_list.filter(id=active_crop["id"]).first() if active_crop else None,
            "procurement": active_crop,
            "timeline": timeline_items,
            "all_farmer_crops": all_farmer_crops,
        },
    )



# ==============================================================================
# PROCUREMENT OFFICER WORKFLOW VIEWS
# ==============================================================================

def _get_officer_records(center):
    if center:
        return ProcurementRecord.objects.filter(
            models.Q(center=center) |
            models.Q(center__isnull=True, produce__district__iexact=center.district)
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

            if hasattr(rec, "appointment") and rec.appointment:
                appt = rec.appointment
                appt.status = "CONFIRMED"
                appt.save()

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
    pending_records = list(base_records.filter(current_stage__in=["REGISTRATION", "APPOINTMENT", "GATE_ENTRY"]))
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else (pending_records[0] if pending_records else None)

    # Ensure selected_record is present in pending_records for selector UI
    if selected_record and selected_record not in pending_records:
        pending_records.insert(0, selected_record)

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

    from tokens.models import Token
    from django.utils import timezone
    today = timezone.now().date()

    current_called_token = None
    waiting_tokens = []
    if center:
        current_called_token = Token.objects.filter(
            procurement_center=center,
            date=today,
            status="CALLED",
        ).select_related("farmer", "produce", "procurement_record").first()

        waiting_tokens = Token.objects.filter(
            procurement_center=center,
            date=today,
            status="WAITING",
        ).select_related("farmer", "produce").order_by("sequence_number")

    return render(
        request,
        "procurement/officer_queue.html",
        {
            "officer": request.user,
            "profile": profile,
            "center": center,
            "active_records": active_records,
            "queue_counts": queue_counts,
            "current_called_token": current_called_token,
            "waiting_tokens": waiting_tokens,
            "waiting_count": len(waiting_tokens),
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
                if result == "PASSED":
                    return redirect(f"/procurement/officer/weighing/?record_id={record.id}")
            except Exception as e:
                messages.error(request, str(e))
            return redirect("procurement:officer_quality_check")

    base_records = _get_officer_records(center)
    pending_records = list(base_records.filter(current_stage__in=["GATE_ENTRY", "QUALITY_CHECK"]))
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else (pending_records[0] if pending_records else None)
    if selected_record and selected_record not in pending_records:
        pending_records.insert(0, selected_record)

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
                return redirect(f"/procurement/officer/acceptance/?record_id={record.id}")
            except Exception as e:
                messages.error(request, str(e))
            return redirect("procurement:officer_weighing")

    base_records = _get_officer_records(center)
    pending_records = list(base_records.filter(current_stage__in=["QUALITY_CHECK", "WEIGHING"]))
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else (pending_records[0] if pending_records else None)
    if selected_record and selected_record not in pending_records:
        pending_records.insert(0, selected_record)

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
                    return redirect(f"/procurement/officer/bills/?record_id={record.id}")
                else:
                    messages.warning(request, f"Procurement REJECTED for Farmer {record.farmer.get_full_name() or record.farmer.username}.")
            except Exception as e:
                messages.error(request, str(e))
            return redirect("procurement:officer_acceptance")

    base_records = _get_officer_records(center)
    pending_records = list(base_records.filter(current_stage__in=["WEIGHING", "ACCEPTANCE"]))
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else (pending_records[0] if pending_records else None)
    if selected_record and selected_record not in pending_records:
        pending_records.insert(0, selected_record)

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
                return redirect(f"/procurement/officer/payments/?record_id={record.id}")
            except Exception as e:
                messages.error(request, str(e))
            return redirect("procurement:officer_bills")

    base_records = _get_officer_records(center)
    pending_records = list(base_records.filter(current_stage__in=["ACCEPTANCE", "BILL_GENERATED"]))
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else (pending_records[0] if pending_records else None)
    if selected_record and selected_record not in pending_records:
        pending_records.insert(0, selected_record)

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
    pending_records = list(base_records.filter(current_stage__in=["BILL_GENERATED", "PAYMENT_INITIATED"]))
    selected_record = base_records.filter(pk=target_pk).first() if target_pk else (pending_records[0] if pending_records else None)
    if selected_record and selected_record not in pending_records:
        pending_records.insert(0, selected_record)

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

