from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect
from produce.models import Produce
from accounts.models import Profile
from procurement.permissions import officer_required
from procurement.models import ProcurementCenter, ProcurementRecord
from procurement.services import sync_all_farmer_procurements


@login_required
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    # Officer approval check
    if profile.role == "OFFICER" and not profile.is_approved:
        return redirect("pending_approval")

    if profile.role == "FARMER":
        return redirect("farmer_dashboard")

    elif profile.role == "OFFICER":
        return redirect("officer_dashboard")

    elif profile.role == "ADMIN":
        return redirect("admin_dashboard")

    return redirect("farmer_dashboard")



STAGE_RANKS = {
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


@login_required
def farmer_dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if profile.role != "FARMER":
        return redirect("dashboard")

    sync_all_farmer_procurements()

    from appointments.models import Appointment
    from tokens.models import Token
    from notifications.models import Notification

    # 1. Fetch all registered produce belonging to the logged-in farmer
    produce_list = Produce.objects.filter(
        farmer=request.user
    ).order_by("-created_at")

    # 2. Build multi-produce journey data (linking Produce -> ProcurementRecord -> Appointment -> Token)
    produce_journeys = []
    for produce in produce_list:
        rec = ProcurementRecord.objects.filter(produce=produce, farmer=request.user).first()
        appt = Appointment.objects.filter(produce=produce, farmer=request.user, status="CONFIRMED").first()
        tok = Token.objects.filter(produce=produce, farmer=request.user, status__in=["WAITING", "CALLED", "IN_PROGRESS"]).first()

        if rec:
            stage = rec.current_stage
            stage_num = STAGE_RANKS.get(stage, 1)
            stage_display = rec.get_current_stage_display()
            center_name = rec.center.name if rec.center else (rec.center_name or "Procurement Center")
            appointment_time = rec.appointment_date or "Slot Assigned"
            token_number = f"#{rec.token_number}" if rec.token_number else "Pending"
        elif appt:
            stage = "APPOINTMENT"
            stage_num = 2
            stage_display = "Appointment Confirmed"
            center_name = appt.procurement_center.name if appt.procurement_center else "Procurement Center"
            appointment_time = f"{appt.appointment_date} ({appt.appointment_time_slot})"
            token_number = f"#{appt.token_number}" if appt.token_number else "Pending"
        elif tok:
            stage = "APPOINTMENT"
            stage_num = 2
            stage_display = f"Token Issued (#{tok.token_number})"
            center_name = tok.procurement_center.name if tok.procurement_center else "Procurement Center"
            appointment_time = f"{tok.date}"
            token_number = f"#{tok.token_number}"
        elif produce.status == "REQUESTED":
            stage = "REQUESTED"
            stage_num = 1
            stage_display = "Procurement Requested"
            center_name = "Awaiting Center Selection"
            appointment_time = "--"
            token_number = "--"
        else:
            stage = "AVAILABLE"
            stage_num = 0
            stage_display = "Available for Procurement"
            center_name = "--"
            appointment_time = "--"
            token_number = "--"

        produce_journeys.append({
            "produce": produce,
            "id": produce.id,
            "crop_name": produce.crop_name,
            "quantity": produce.quantity,
            "unit": produce.get_unit_display(),
            "status": produce.status,
            "stage": stage,
            "stage_num": stage_num,
            "stage_display": stage_display,
            "center_name": center_name,
            "appointment_time": appointment_time,
            "token_number": token_number,
            "record": rec,
            "appointment": appt,
            "token": tok,
        })

    # 3. Determine active journey for detailed timeline view
    target_produce_id = request.GET.get("produce_id")
    active_journey = None
    if target_produce_id:
        active_journey = next((j for j in produce_journeys if str(j["id"]) == str(target_produce_id)), None)
    if not active_journey:
        active_journey = next((j for j in produce_journeys if j["stage_num"] > 0), None) or (produce_journeys[0] if produce_journeys else None)

    # 4. Fetch all active/upcoming appointments for the farmer
    active_appointments = Appointment.objects.filter(
        farmer=request.user,
        status="CONFIRMED"
    ).select_related("produce", "procurement_record", "procurement_center").order_by("appointment_date", "appointment_time_slot")

    # 5. Fetch all active tokens for the farmer
    active_tokens = Token.objects.filter(
        farmer=request.user,
        status__in=["WAITING", "CALLED", "IN_PROGRESS"],
    ).select_related("procurement_center", "produce", "appointment").order_by("date", "sequence_number")

    # 6. Fetch financial & payment records per produce
    payment_records = []
    total_payout_processing = 0.0
    total_payout_completed = 0.0

    records_with_fin = ProcurementRecord.objects.filter(
        farmer=request.user
    ).select_related("produce", "center").prefetch_related("bill", "payment_record").order_by("-updated_at")

    for rec in records_with_fin:
        bill = getattr(rec, "bill", None)
        payment_rec = getattr(rec, "payment_record", None)
        amt = float(bill.net_amount) if bill else float(rec.total_amount or 0.0)
        st = payment_rec.get_payment_status_display() if payment_rec else rec.payment_status

        if amt > 0 or rec.current_stage in ["BILL_GENERATED", "PAYMENT_INITIATED", "PAYMENT_RECEIVED", "COMPLETED"]:
            payment_records.append({
                "crop_name": rec.crop_name,
                "quantity": f"{rec.actual_quantity or rec.registered_quantity} {rec.unit}",
                "center": rec.center_display_name,
                "amount": amt,
                "status": st,
                "stage": rec.get_current_stage_display(),
            })
            if st in ["Received", "Completed", "PAYMENT_RECEIVED", "COMPLETED"] or rec.current_stage in ["PAYMENT_RECEIVED", "COMPLETED"]:
                total_payout_completed += amt
            else:
                total_payout_processing += amt

    # 7. Fetch recent notifications
    recent_notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")[:5]

    unread_notifications_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    # 8. Summary statistics
    summary = {
        "total_produce": produce_list.count(),
        "requested_procurements": produce_list.filter(status="REQUESTED").count(),
        "active_appointments": active_appointments.count(),
        "active_tokens": active_tokens.count(),
        "completed_procurements": ProcurementRecord.objects.filter(farmer=request.user, current_stage="COMPLETED").count(),
        "payout_processing": total_payout_processing,
        "payout_completed": total_payout_completed,
    }

    return render(
        request,
        "farmer/dashboard.html",
        {
            "farmer": request.user,
            "profile": profile,
            "summary": summary,
            "produce_count": produce_list.count(),
            "produce_list": produce_list,
            "produce_journeys": produce_journeys,
            "active_journey": active_journey,
            "current_produce": active_journey["produce"] if active_journey else None,
            "procurement_record": active_journey["record"] if active_journey else None,
            "procurement_stage_num": active_journey["stage_num"] if active_journey else 1,
            "active_appointments": active_appointments,
            "active_appointment": active_appointments.first(),
            "active_tokens": active_tokens,
            "active_token": active_tokens.first(),
            "payment_records": payment_records,
            "recent_notifications": recent_notifications,
            "unread_notifications_count": unread_notifications_count,
        }
    )



@login_required
@officer_required
def officer_dashboard(request):
    sync_all_farmer_procurements()

    profile = request.user.profile
    center = profile.assigned_center

    if not center:
        center = ProcurementCenter.objects.filter(is_active=True).first()
        if center:
            profile.assigned_center = center
            profile.save()

    if center:
        records = ProcurementRecord.objects.filter(
            Q(center=center) |
            Q(center__isnull=True, produce__district__iexact=center.district)
        ).distinct()
    else:
        records = ProcurementRecord.objects.all()

    today_summary = {
        "total_appointments": records.count(),
        "arrived": records.filter(current_stage__in=["GATE_ENTRY", "QUALITY_CHECK", "WEIGHING", "ACCEPTANCE", "BILL_GENERATED", "PAYMENT_INITIATED", "PAYMENT_RECEIVED", "COMPLETED"]).count(),
        "waiting": records.filter(current_stage__in=["GATE_ENTRY", "QUALITY_CHECK", "WEIGHING"]).count(),
        "completed": records.filter(current_stage="COMPLETED").count(),
        "rejected": records.filter(current_stage="REJECTED").count(),
        "current_token": (cur.token_number if (cur := records.filter(current_stage__in=["GATE_ENTRY", "QUALITY_CHECK"]).first()) else "A-101"),
        "next_token": (nxt.token_number if (nxt := records.filter(current_stage="APPOINTMENT").first()) else "A-102"),
    }

    pending_actions = {
        "gate_entry": records.filter(current_stage__in=["REGISTRATION", "APPOINTMENT"]).count(),
        "quality_check": records.filter(current_stage="GATE_ENTRY").count(),
        "weighing": records.filter(current_stage="QUALITY_CHECK").count(),
        "acceptance": records.filter(current_stage="WEIGHING").count(),
        "bills": records.filter(current_stage="ACCEPTANCE").count(),
        "payments": records.filter(current_stage="BILL_GENERATED").count(),
    }

    recent_records = records[:8]

    return render(
        request,
        "officer/dashboard.html",
        {
            "officer": request.user,
            "profile": profile,
            "center": center,
            "today": today_summary,
            "pending": pending_actions,
            "recent_records": recent_records,
            "gate_entries_today": today_summary["arrived"],
            "pending_quality": pending_actions["quality_check"],
            "pending_weighing": pending_actions["weighing"],
            "pending_acceptance": pending_actions["acceptance"],
            "pending_bills": pending_actions["bills"],
            "pending_payments": pending_actions["payments"],
            "completed_today": today_summary["completed"],
            "total_appointments": today_summary["total_appointments"],
        },
    )


@login_required
def admin_dashboard(request):
    return redirect("admin:index")