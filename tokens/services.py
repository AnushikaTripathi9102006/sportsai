import uuid
from django.db import models, transaction
from django.utils import timezone
from .models import Token


def generate_token_for_appointment(appointment):
    """
    Safely generates or retrieves a unique Token for an appointment.
    Ensures concurrency safety via atomic database transaction and sequence locking.
    """
    if hasattr(appointment, "token_obj") and appointment.token_obj:
        return appointment.token_obj

    record = appointment.procurement_record
    if hasattr(record, "token_obj") and record.token_obj:
        tok = record.token_obj
        if tok.appointment is None:
            tok.appointment = appointment
            tok.save()
        return tok

    center = appointment.procurement_center
    appt_date = appointment.appointment_date

    with transaction.atomic():
        last_seq = (
            Token.objects.filter(
                procurement_center=center,
                date=appt_date,
            )
            .select_for_update()
            .aggregate(max_seq=models.Max("sequence_number"))["max_seq"]
            or 0
        )

        next_seq = last_seq + 1
        prefix = (center.district[:3] if center and center.district else "LKO").upper()
        token_no = f"{prefix}-{next_seq:03d}"

        token = Token.objects.create(
            token_number=token_no,
            sequence_number=next_seq,
            farmer=appointment.farmer,
            produce=appointment.produce,
            procurement_record=record,
            appointment=appointment,
            procurement_center=center,
            date=appt_date,
            counter_number=record.counter_number or "Counter 1",
            status="WAITING",
        )

        # Sync token number to record and appointment
        record.token_number = token_no
        record.save()

        appointment.token_number = token_no
        appointment.save()

        try:
            from notifications.services import notify_farmer
            notify_farmer(
                farmer_user=appointment.farmer,
                title="🎟️ Token Generated",
                message=f"Your procurement token #{token_no} has been generated for {appointment.produce.crop_name}. Arrive at {center.name} on {appt_date.strftime('%d %b %Y')}.",
                notification_type="TOKEN",
                target_url="/tokens/",
                related_object=token,
                event_key=f"token_gen_{token.id}",
            )
        except Exception:
            pass

        return token


def call_next_token(officer, center):
    """
    Calls the next WAITING token at the officer's center for today.
    Updates status to CALLED atomically.
    """
    today = timezone.now().date()
    with transaction.atomic():
        next_token = (
            Token.objects.filter(
                procurement_center=center,
                date=today,
                status="WAITING",
            )
            .select_for_update()
            .order_by("sequence_number")
            .first()
        )

        if not next_token:
            return None, "No farmers are currently waiting in the queue for today."

        next_token.status = "CALLED"
        next_token.called_at = timezone.now()
        next_token.save()

        try:
            from notifications.services import notify_farmer
            notify_farmer(
                farmer_user=next_token.farmer,
                title="🚜 Your Turn!",
                message=f"Your token #{next_token.token_number} is now being called! Please proceed immediately to {next_token.counter_number} at {center.name}.",
                notification_type="TOKEN",
                target_url="/tokens/",
                related_object=next_token,
                event_key=f"token_called_{next_token.id}_{next_token.called_at.timestamp()}",
            )
        except Exception:
            pass

        return next_token, f"Token {next_token.token_number} called successfully to {next_token.counter_number}."


def sync_token_stage(procurement_record, target_stage):
    """
    Keeps Token status in sync with ProcurementRecord stage machine.
    """
    if not hasattr(procurement_record, "token_obj"):
        return None

    token = procurement_record.token_obj
    if target_stage in ["GATE_ENTRY", "QUALITY_CHECK", "WEIGHING", "ACCEPTANCE", "BILL_GENERATED", "PAYMENT_INITIATED"]:
        if token.status != "IN_PROGRESS":
            token.status = "IN_PROGRESS"
            token.save()
    elif target_stage in ["COMPLETED", "PAYMENT_RECEIVED"]:
        token.status = "COMPLETED"
        token.completed_at = timezone.now()
        token.save()
    elif target_stage == "CANCELLED":
        token.status = "CANCELLED"
        token.save()
    elif target_stage == "REJECTED":
        token.status = "MISSED"
        token.save()

    return token
