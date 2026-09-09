from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from produce.models import Produce
from procurement.models import ProcurementRecord
from procurement.services import sync_all_farmer_procurements
from .forms import AppointmentBookingForm
from .models import Appointment


@login_required
def appointments(request):
    sync_all_farmer_procurements()

    all_appointments = Appointment.objects.filter(
        farmer=request.user
    ).select_related("produce", "procurement_record", "procurement_center").order_by("appointment_date", "appointment_time_slot")

    upcoming_appointments = all_appointments.filter(status="CONFIRMED")
    completed_appointments = all_appointments.filter(status="COMPLETED")
    cancelled_appointments = all_appointments.filter(status="CANCELLED")

    # Fetch eligible produce without an active appointment
    eligible_produces = Produce.objects.filter(
        farmer=request.user,
        status="REQUESTED",
    ).exclude(appointments__status="CONFIRMED")

    selected_produce_id = request.GET.get("produce_id")
    active_appointment = None
    if selected_produce_id:
        active_appointment = upcoming_appointments.filter(produce_id=selected_produce_id).first()
    if not active_appointment:
        active_appointment = upcoming_appointments.first()

    return render(
        request,
        "appointments/appointments.html",
        {
            "upcoming_appointments": upcoming_appointments,
            "completed_appointments": completed_appointments,
            "cancelled_appointments": cancelled_appointments,
            "active_appointment": active_appointment,
            "eligible_produces": eligible_produces,
            "all_appointments": all_appointments,
            "total_upcoming_count": upcoming_appointments.count(),
        },
    )


from procurement.models import ProcurementCenter


@login_required
def book_appointment(request):
    sync_all_farmer_procurements()

    eligible_produces = Produce.objects.filter(
        farmer=request.user,
        status="REQUESTED",
    ).exclude(appointments__status="CONFIRMED")

    selected_produce_id = request.GET.get("produce_id") or request.POST.get("produce_id")
    selected_produce = None

    if selected_produce_id:
        selected_produce = eligible_produces.filter(pk=selected_produce_id).first()
    if not selected_produce:
        selected_produce = eligible_produces.first()

    # Center selection override via URL parameter or existing procurement record
    selected_center_id = request.GET.get("center_id") or request.POST.get("center_id")
    selected_center = None
    if selected_center_id:
        selected_center = ProcurementCenter.objects.filter(pk=selected_center_id, is_active=True).first()

    procurement_record = None
    if selected_produce:
        procurement_record = ProcurementRecord.objects.filter(produce=selected_produce, farmer=request.user).first()
        if not selected_center and procurement_record and procurement_record.center:
            selected_center = procurement_record.center

        # If user explicitly passed center_id, ensure procurement_record exists and has selected_center set
        if selected_center:
            if not procurement_record:
                procurement_record = ProcurementRecord.objects.create(
                    produce=selected_produce,
                    farmer=request.user,
                    crop_name=selected_produce.crop_name,
                    registered_quantity=selected_produce.quantity,
                    unit=selected_produce.get_unit_display(),
                    center=selected_center,
                    center_name=selected_center.name,
                    current_stage="REGISTRATION",
                )
            elif procurement_record.center != selected_center:
                procurement_record.center = selected_center
                procurement_record.center_name = selected_center.name
                procurement_record.save()

    # Generate available dates (next 7 days starting from tomorrow)
    today = date.today()
    available_dates = [today + timedelta(days=i) for i in range(1, 8)]

    selected_date_str = request.GET.get("date") or request.POST.get("appointment_date")
    selected_date = available_dates[0]

    if selected_date_str:
        try:
            parsed_date = date.fromisoformat(selected_date_str)
            if parsed_date >= today:
                selected_date = parsed_date
        except ValueError:
            pass

    slots_availability = []
    if selected_center:
        for slot_code, slot_label in Appointment.TIME_SLOT_CHOICES:
            booked_count = Appointment.objects.filter(
                procurement_center=selected_center,
                appointment_date=selected_date,
                appointment_time_slot=slot_code,
                status="CONFIRMED",
            ).count()

            remaining = max(0, Appointment.SLOT_CAPACITY - booked_count)
            is_available = remaining > 0

            slots_availability.append({
                "code": slot_code,
                "label": slot_label,
                "booked_count": booked_count,
                "remaining": remaining,
                "is_available": is_available,
                "capacity": Appointment.SLOT_CAPACITY,
            })

    form = AppointmentBookingForm(
        request.POST or None,
        user=request.user,
        initial={
            "produce_id": selected_produce.id if selected_produce else "",
            "appointment_date": selected_date.isoformat(),
        },
    )

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "review" and form.is_valid():
            cleaned_data = form.cleaned_data
            cnt_obj = selected_center or cleaned_data["center_obj"]
            return render(
                request,
                "appointments/confirm.html",
                {
                    "produce": cleaned_data["produce_obj"],
                    "record": cleaned_data["record_obj"],
                    "center": cnt_obj,
                    "appointment_date": cleaned_data["appointment_date"],
                    "appointment_time_slot": cleaned_data["appointment_time_slot"],
                    "token_number": cleaned_data["record_obj"].token_number or f"TK-{cleaned_data['produce_obj'].id:04d}",
                },
            )
        elif action == "confirm" and form.is_valid():
            cleaned_data = form.cleaned_data
            prod_obj = cleaned_data["produce_obj"]
            rec_obj = cleaned_data["record_obj"]
            cnt_obj = selected_center or cleaned_data["center_obj"]
            appt_date = cleaned_data["appointment_date"]
            time_slot = cleaned_data["appointment_time_slot"]

            # Capacity safety check
            booked_count = Appointment.objects.filter(
                procurement_center=cnt_obj,
                appointment_date=appt_date,
                appointment_time_slot=time_slot,
                status="CONFIRMED",
            ).count()

            if booked_count >= Appointment.SLOT_CAPACITY:
                messages.error(request, f"The selected slot ({time_slot}) is now full at {cnt_obj.name}. Please select another slot.")
                return redirect(f"/appointments/book/?produce_id={prod_obj.id}&center_id={cnt_obj.id}")

            with transaction.atomic():
                appointment = Appointment.objects.create(
                    farmer=request.user,
                    produce=prod_obj,
                    procurement_record=rec_obj,
                    procurement_center=cnt_obj,
                    appointment_date=appt_date,
                    appointment_time_slot=time_slot,
                    status="CONFIRMED",
                )

                # Sync procurement record
                rec_obj.center = cnt_obj
                rec_obj.center_name = cnt_obj.name
                rec_obj.appointment_date = f"{appt_date.strftime('%d %b %Y')} ({time_slot})"
                if rec_obj.current_stage == "REGISTRATION":
                    rec_obj.current_stage = "APPOINTMENT"
                rec_obj.save()

                from tokens.services import generate_token_for_appointment
                token_obj = generate_token_for_appointment(appointment)

                from notifications.services import notify_farmer, notify_officer
                notify_farmer(
                    farmer_user=request.user,
                    title="📅 Appointment Confirmed",
                    message=f"Your procurement appointment for {prod_obj.crop_name} has been confirmed for {appt_date.strftime('%d %b %Y')} ({time_slot}) at {cnt_obj.name}. Token: #{token_obj.token_number}.",
                    notification_type="APPOINTMENT",
                    target_url=f"/appointments/detail/{appointment.pk}/",
                    related_object=appointment,
                    event_key=f"appt_conf_{appointment.id}",
                )

                # Notify officers at the selected center
                from accounts.models import Profile
                officers = Profile.objects.filter(role="OFFICER", assigned_center=cnt_obj)
                for p in officers:
                    notify_officer(
                        officer_user=p.user,
                        title="📦 New Farmer Registration",
                        message=f"New farmer registration received: {request.user.get_full_name() or request.user.username} ({prod_obj.crop_name}, {prod_obj.quantity} Quintals) scheduled for {appt_date.strftime('%d %b %Y')} ({time_slot}). Token: #{token_obj.token_number}.",
                        notification_type="PROCUREMENT",
                        target_url="/procurement/officer/appointments/",
                        related_object=appointment,
                        event_key=f"officer_reg_{appointment.id}_{p.user.id}",
                    )

            messages.success(
                request,
                f"Appointment successfully confirmed for {prod_obj.crop_name} at {cnt_obj.name} on {appt_date.strftime('%d %b %Y')} ({time_slot})! Token: #{token_obj.token_number}"
            )
            return redirect("appointments:appointment_detail", pk=appointment.pk)

    return render(
        request,
        "appointments/book.html",
        {
            "eligible_produces": eligible_produces,
            "selected_produce": selected_produce,
            "procurement_record": procurement_record,
            "center": selected_center,
            "available_dates": available_dates,
            "selected_date": selected_date,
            "slots_availability": slots_availability,
            "form": form,
        },
    )


@login_required
def reschedule_appointment(request, pk):
    """
    Farmer Appointment Rescheduling Workflow.
    Allows farmer to view dynamic center recommendations, pick a center (same or new),
    select a new date/slot, cancel old appointment & token, and assign new appointment & token.
    """
    sync_all_farmer_procurements()

    old_appointment = get_object_or_404(
        Appointment.objects.select_related("produce", "procurement_record", "procurement_center"),
        pk=pk,
        farmer=request.user,
    )

    record = old_appointment.procurement_record
    if not record:
        messages.error(request, "Associated procurement record not found.")
        return redirect("appointments:appointments")

    # IMPORTANT BUSINESS RULE: Rescheduling disabled once actual procurement processing has started
    if record.current_stage not in ["REGISTRATION", "APPOINTMENT"]:
        messages.error(
            request,
            f"Rescheduling is disabled because your procurement has already reached the '{record.get_current_stage_display()}' stage at the center."
        )
        return redirect("appointments:appointment_detail", pk=pk)

    produce = old_appointment.produce

    # Recalculate intelligent center recommendations
    from procurement.recommendation_engine import get_recommended_centers
    target_district = request.GET.get("district") or produce.district
    top_rec, ranked_centers = get_recommended_centers(produce=produce, farmer=request.user, target_district=target_district)

    selected_center_id = request.GET.get("center_id") or request.POST.get("center_id")
    selected_center = None
    if selected_center_id:
        selected_center = ProcurementCenter.objects.filter(pk=selected_center_id, is_active=True).first()
    if not selected_center:
        selected_center = old_appointment.procurement_center or top_rec

    today = date.today()
    available_dates = [today + timedelta(days=i) for i in range(1, 8)]

    selected_date_str = request.GET.get("date") or request.POST.get("appointment_date")
    selected_date = available_dates[0]
    if selected_date_str:
        try:
            parsed_date = date.fromisoformat(selected_date_str)
            if parsed_date >= today:
                selected_date = parsed_date
        except ValueError:
            pass

    slots_availability = []
    if selected_center:
        for slot_code, slot_label in Appointment.TIME_SLOT_CHOICES:
            booked_count = Appointment.objects.filter(
                procurement_center=selected_center,
                appointment_date=selected_date,
                appointment_time_slot=slot_code,
                status="CONFIRMED",
            ).exclude(pk=old_appointment.pk).count()

            remaining = max(0, Appointment.SLOT_CAPACITY - booked_count)
            is_available = remaining > 0

            slots_availability.append({
                "code": slot_code,
                "label": slot_label,
                "booked_count": booked_count,
                "remaining": remaining,
                "is_available": is_available,
                "capacity": Appointment.SLOT_CAPACITY,
            })

    if request.method == "POST":
        new_center_id = request.POST.get("center_id")
        new_date_str = request.POST.get("appointment_date")
        new_slot = request.POST.get("appointment_time_slot")

        if new_center_id and new_date_str and new_slot:
            new_center = get_object_or_404(ProcurementCenter, pk=new_center_id, is_active=True)
            try:
                new_date = date.fromisoformat(new_date_str)
            except ValueError:
                new_date = selected_date

            # Capacity check
            booked = Appointment.objects.filter(
                procurement_center=new_center,
                appointment_date=new_date,
                appointment_time_slot=new_slot,
                status="CONFIRMED",
            ).exclude(pk=old_appointment.pk).count()

            if booked >= Appointment.SLOT_CAPACITY:
                messages.error(request, "The selected slot is full. Please choose another time slot or date.")
            else:
                old_center = old_appointment.procurement_center
                with transaction.atomic():
                    # 1. Mark old appointment cancelled/rescheduled
                    old_appointment.status = "CANCELLED"
                    old_appointment.save()

                    # 2. Mark old tokens inactive
                    from tokens.models import Token
                    Token.objects.filter(appointment=old_appointment).update(status="CANCELLED")
                    Token.objects.filter(procurement_record=record, status="WAITING").update(status="CANCELLED")

                    # 3. Create NEW Appointment
                    new_appointment = Appointment.objects.create(
                        farmer=request.user,
                        produce=produce,
                        procurement_record=record,
                        procurement_center=new_center,
                        appointment_date=new_date,
                        appointment_time_slot=new_slot,
                        status="CONFIRMED",
                    )

                    # 4. Update procurement record
                    record.center = new_center
                    record.center_name = new_center.name
                    record.appointment_date = f"{new_date.strftime('%d %b %Y')} ({new_slot})"
                    if record.current_stage == "REGISTRATION":
                        record.current_stage = "APPOINTMENT"
                    record.save()

                    # 5. Generate NEW token for new appointment
                    from tokens.services import generate_token_for_appointment
                    new_token = generate_token_for_appointment(new_appointment)

                    # 6. Notify farmer
                    from notifications.services import notify_farmer, notify_officer
                    notify_farmer(
                        farmer_user=request.user,
                        title="📅 Appointment Rescheduled",
                        message=f"Your procurement appointment for {produce.crop_name} has been rescheduled to {new_date.strftime('%d %b %Y')} ({new_slot}) at {new_center.name}. New token: #{new_token.token_number}.",
                        notification_type="APPOINTMENT",
                        target_url=f"/appointments/detail/{new_appointment.pk}/",
                        related_object=new_appointment,
                        event_key=f"appt_resched_{new_appointment.id}",
                    )

                    # 7. Notify new center officers
                    from accounts.models import Profile
                    new_officers = Profile.objects.filter(role="OFFICER", assigned_center=new_center)
                    for p in new_officers:
                        notify_officer(
                            officer_user=p.user,
                            title="📦 Rescheduled Farmer Registration",
                            message=f"Farmer {request.user.get_full_name() or request.user.username} ({produce.crop_name}) has rescheduled their appointment to your center ({new_center.name}) for {new_date.strftime('%d %b %Y')} ({new_slot}). Token: #{new_token.token_number}.",
                            notification_type="PROCUREMENT",
                            target_url="/procurement/officer/appointments/",
                            related_object=new_appointment,
                            event_key=f"off_resched_new_{new_appointment.id}_{p.user.id}",
                        )

                    # 8. Notify old center officers if center changed
                    if old_center and old_center != new_center:
                        old_officers = Profile.objects.filter(role="OFFICER", assigned_center=old_center)
                        for p in old_officers:
                            notify_officer(
                                officer_user=p.user,
                                title="ℹ️ Registration Transferred",
                                message=f"Farmer {request.user.get_full_name() or request.user.username} ({produce.crop_name}) has rescheduled their appointment to a different center ({new_center.name}).",
                                notification_type="PROCUREMENT",
                                target_url="/procurement/officer/appointments/",
                                related_object=old_appointment,
                                event_key=f"off_resched_old_{old_appointment.id}_{p.user.id}",
                            )

                messages.success(
                    request,
                    f"Appointment successfully rescheduled to {new_center.name} on {new_date.strftime('%d %b %Y')} ({new_slot})! New Token: #{new_token.token_number}."
                )
                return redirect("appointments:appointment_detail", pk=new_appointment.pk)

    return render(
        request,
        "appointments/reschedule.html",
        {
            "old_appointment": old_appointment,
            "produce": produce,
            "record": record,
            "top_rec": top_rec,
            "ranked_centers": ranked_centers,
            "selected_center": selected_center,
            "available_dates": available_dates,
            "selected_date": selected_date,
            "slots_availability": slots_availability,
        },
    )


@login_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "produce", "procurement_record", "procurement_center", "farmer"
        ),
        pk=pk,
        farmer=request.user,
    )

    record = appointment.procurement_record

    STAGE_ORDER = [
        ("REGISTRATION", "Produce Registered"),
        ("APPOINTMENT", "Appointment Confirmed"),
        ("GATE_ENTRY", "Gate Entry Checked-in"),
        ("QUALITY_CHECK", "Quality Inspected"),
        ("WEIGHING", "Weighing Recorded"),
        ("ACCEPTANCE", "Procurement Accepted"),
        ("BILL_GENERATED", "Bill Generated"),
        ("PAYMENT_INITIATED", "Payment Initiated"),
        ("COMPLETED", "Payment Received & Completed"),
    ]

    current_stage = record.current_stage if record else "APPOINTMENT"
    current_index = 1

    for idx, (st_code, st_name) in enumerate(STAGE_ORDER):
        if st_code == current_stage:
            current_index = idx
            break

    timeline = []
    for idx, (st_code, st_label) in enumerate(STAGE_ORDER):
        if idx < current_index:
            st_state = "done"
        elif idx == current_index:
            st_state = "current"
        else:
            st_state = "pending"

        timeline.append({
            "code": st_code,
            "label": st_label,
            "state": st_state,
        })

    return render(
        request,
        "appointments/detail.html",
        {
            "appointment": appointment,
            "record": record,
            "timeline": timeline,
            "can_cancel": appointment.can_be_cancelled(),
        },
    )


@login_required
def cancel_appointment(request, pk):
    appointment = get_object_or_404(
        Appointment,
        pk=pk,
        farmer=request.user,
    )

    if not appointment.can_be_cancelled():
        messages.error(request, "This appointment cannot be cancelled because procurement has already entered center inspection or gate entry.")
        return redirect("appointments:appointment_detail", pk=appointment.pk)

    if request.method == "POST":
        with transaction.atomic():
            appointment.status = "CANCELLED"
            appointment.save()

            record = appointment.procurement_record
            if record:
                record.current_stage = "CANCELLED"
                record.save()

                from tokens.services import sync_token_stage
                sync_token_stage(record, "CANCELLED")

                from notifications.services import notify_farmer
                notify_farmer(
                    farmer_user=request.user,
                    title="❌ Appointment Cancelled",
                    message=f"Your procurement appointment for {appointment.produce.crop_name} has been cancelled.",
                    notification_type="APPOINTMENT",
                    target_url="/appointments/",
                    related_object=appointment,
                    event_key=f"appt_cancel_{appointment.id}",
                )

        messages.success(request, f"Appointment APT-{appointment.id:04d} has been cancelled successfully.")
        return redirect("appointments:appointments")

    return render(
        request,
        "appointments/cancel_confirm.html",
        {
            "appointment": appointment,
        },
    )
