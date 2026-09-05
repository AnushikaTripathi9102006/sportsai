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

    produce_list = Produce.objects.filter(
        farmer=request.user
    ).order_by("-created_at")

    current_produce = produce_list.filter(
        status="REQUESTED"
    ).first() or produce_list.first()

    procurement_record = ProcurementRecord.objects.filter(
        farmer=request.user
    ).order_by("-created_at").first()

    stage_num = 1
    if procurement_record:
        stage_num = STAGE_RANKS.get(procurement_record.current_stage, 1)

    return render(
        request,
        "farmer/dashboard.html",
        {
            "farmer": request.user,
            "profile": profile,
            "produce_count": produce_list.count(),
            "produce_list": produce_list[:3],
            "current_produce": current_produce,
            "procurement_record": procurement_record,
            "procurement_stage_num": stage_num,
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
            Q(
                Q(center=center),
                Q(center__district__iexact=center.district),
                Q(produce__district__iexact=center.district),
                Q(center__isnull=True),
                _connector=Q.OR,
            )
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