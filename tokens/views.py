from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from procurement.permissions import officer_required
from procurement.services import sync_all_farmer_procurements
from produce.models import Produce
from .models import Token
from .services import (
    call_next_token,
    generate_token_for_appointment,
    sync_token_stage,
)


@login_required
def token_queue(request):
    sync_all_farmer_procurements()
    profile = getattr(request.user, "profile", None)

    # 1. Auto-generate tokens for ALL confirmed appointments without active tokens
    confirmed_appts = Appointment.objects.filter(
        farmer=request.user,
        status="CONFIRMED",
    ).select_related("produce", "procurement_record", "procurement_center")

    for appt in confirmed_appts:
        has_token = Token.objects.filter(
            farmer=request.user,
            produce=appt.produce,
            status__in=["WAITING", "CALLED", "IN_PROGRESS"],
        ).exists()
        if not has_token:
            generate_token_for_appointment(appt)

    # 2. Fetch all active tokens for farmer
    all_active_tokens = (
        Token.objects.filter(
            farmer=request.user,
            status__in=["WAITING", "CALLED", "IN_PROGRESS"],
        )
        .select_related("produce", "procurement_record", "procurement_center", "appointment")
        .order_by("date", "sequence_number")
    )

    selected_produce_id = request.GET.get("produce_id")
    selected_token_id = request.GET.get("token_id")
    active_token = None

    if selected_token_id:
        active_token = all_active_tokens.filter(pk=selected_token_id).first()
    if not active_token and selected_produce_id:
        active_token = all_active_tokens.filter(produce_id=selected_produce_id).first()
    if not active_token:
        active_token = all_active_tokens.first()

    # Demo override query param ?turn=true
    demo_turn = request.GET.get("turn") == "true"

    token_number = None
    queue_data = None
    active_produce = None
    qr_verify_url = ""

    if active_token:
        active_produce = active_token.produce
        token_number = active_token.token_number
        is_your_turn = active_token.is_your_turn() or demo_turn

        current_serving = Token.objects.filter(
            procurement_center=active_token.procurement_center,
            date=active_token.date,
            status__in=["CALLED", "IN_PROGRESS"],
        ).first()

        current_token_str = (
            current_serving.token_number
            if current_serving
            else (token_number if is_your_turn else f"{active_token.procurement_center.district[:3].upper()}-001")
        )

        your_position = 1 if is_your_turn else active_token.get_queue_position()
        farmers_ahead = 0 if is_your_turn else active_token.get_farmers_ahead()
        estimated_wait = "Immediate (Your Turn)" if is_your_turn else active_token.get_estimated_wait_display()

        qr_verify_url = request.build_absolute_uri(
            reverse("tokens:verify_token", kwargs={"qr_uuid": active_token.secure_qr_uuid})
        )

        queue_data = {
            "current_token": current_token_str,
            "your_position": your_position,
            "farmers_ahead": farmers_ahead,
            "estimated_wait": estimated_wait,
            "is_your_turn": is_your_turn,
            "counter_number": active_token.counter_number or "Counter 1",
            "center_name": active_token.procurement_center.name,
            "qr_verify_url": qr_verify_url,
        }

    return render(
        request,
        "tokens/token_queue.html",
        {
            "farmer": request.user,
            "profile": profile,
            "all_active_tokens": all_active_tokens,
            "active_produce": active_produce,
            "active_token": active_token,
            "token_number": token_number,
            "queue": queue_data,
            "is_your_turn": queue_data["is_your_turn"] if queue_data else False,
        },
    )


@login_required
@officer_required
def call_next_token_view(request):
    if request.method == "POST":
        profile = request.user.profile
        center = profile.assigned_center

        if not center:
            messages.error(request, "You must be assigned to a Procurement Center before calling tokens.")
            return redirect("procurement:officer_queue")

        token, msg = call_next_token(request.user, center)
        if token:
            messages.success(request, msg)
        else:
            messages.warning(request, msg)

    return redirect("procurement:officer_queue")


@login_required
def verify_token_view(request, qr_uuid):
    token = get_object_or_404(
        Token.objects.select_related("farmer", "produce", "procurement_record", "procurement_center"),
        secure_qr_uuid=qr_uuid,
    )

    profile = getattr(request.user, "profile", None)

    # If officer scans/opens token verification, transition token & redirect to Gate Entry
    if profile and profile.role == "OFFICER" and profile.is_approved:
        rec = token.procurement_record
        if token.status in ["WAITING", "CALLED"]:
            token.status = "IN_PROGRESS"
            token.save()

        if rec and rec.current_stage in ["REGISTRATION", "APPOINTMENT"]:
            rec.current_stage = "GATE_ENTRY"
            rec.is_identity_verified = True
            rec.is_produce_verified = True
            rec.verified_by = request.user.get_full_name() or request.user.username
            rec.gate_entry_at = timezone.now()
            rec.save()

        messages.success(
            request,
            f"Token #{token.token_number} verified for Farmer {token.farmer.get_full_name() or token.farmer.username}!"
        )
        return redirect(f"/procurement/officer/gate-entry/?record_id={rec.id}")

    return render(
        request,
        "tokens/verify.html",
        {
            "token": token,
            "record": token.procurement_record,
        },
    )
