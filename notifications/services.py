from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from .models import Notification

User = get_user_model()


def create_notification(
    user,
    title,
    message,
    notification_type="GENERAL",
    target_url="",
    related_object=None,
    event_key=None,
):
    """
    Centralized notification creator with idempotency protection.
    If `event_key` is provided and a notification already exists for this user with that key,
    it returns the existing notification without creating a duplicate.
    """
    if not user or not user.is_authenticated:
        return None

    if event_key:
        existing = Notification.objects.filter(user=user, event_key=event_key).first()
        if existing:
            return existing

    rel_type = ""
    rel_id = None
    if related_object:
        rel_type = related_object.__class__.__name__
        rel_id = getattr(related_object, "pk", getattr(related_object, "id", None))

    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url,
        related_object_type=rel_type,
        related_object_id=rel_id,
        event_key=event_key or "",
    )


def notify_farmer(
    farmer_user,
    title,
    message,
    notification_type="GENERAL",
    target_url="",
    related_object=None,
    event_key=None,
):
    return create_notification(
        user=farmer_user,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url,
        related_object=related_object,
        event_key=event_key,
    )


def notify_officer(
    officer_user,
    title,
    message,
    notification_type="GENERAL",
    target_url="",
    related_object=None,
    event_key=None,
):
    return create_notification(
        user=officer_user,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url,
        related_object=related_object,
        event_key=event_key,
    )


def notify_admin(
    title,
    message,
    notification_type="SYSTEM",
    target_url="",
    related_object=None,
    event_key=None,
):
    admins = User.objects.filter(
        models.Q(is_superuser=True) | models.Q(is_staff=True) | models.Q(profile__role="ADMIN")
    ).distinct()

    created_list = []
    for admin_user in admins:
        notif = create_notification(
            user=admin_user,
            title=title,
            message=message,
            notification_type=notification_type,
            target_url=target_url,
            related_object=related_object,
            event_key=f"{event_key}_admin_{admin_user.id}" if event_key else None,
        )
        if notif:
            created_list.append(notif)
    return created_list


def sync_farmer_notifications(farmer_user):
    """
    Scans farmer's registered produce, appointments, tokens, and procurement records
    and automatically creates idempotent notifications for every step of the procurement process.
    """
    if not farmer_user or not farmer_user.is_authenticated:
        return

    try:
        from produce.models import Produce
        from appointments.models import Appointment
        from tokens.models import Token
        from procurement.models import ProcurementRecord

        # 1. Produce Registration Step
        produces = Produce.objects.filter(farmer=farmer_user)
        for p in produces:
            create_notification(
                user=farmer_user,
                title=f"🌾 Produce Registered: {p.crop_name}",
                message=f"Your produce '{p.crop_name}' ({p.quantity} {p.get_unit_display()}) in {p.district} district has been registered for MSP procurement.",
                notification_type="PRODUCE",
                target_url="/produce/",
                related_object=p,
                event_key=f"produce_reg_{p.id}",
            )

        # 2. Appointment Booking Step
        appointments = Appointment.objects.filter(farmer=farmer_user).select_related("procurement_center", "produce")
        for a in appointments:
            center_name = a.procurement_center.name if a.procurement_center else "Procurement Center"
            crop = a.produce.crop_name if a.produce else "Produce"
            appt_date_str = a.appointment_date.strftime('%d %b %Y') if hasattr(a.appointment_date, 'strftime') else str(a.appointment_date)
            slot_str = a.get_appointment_time_slot_display() if hasattr(a, 'get_appointment_time_slot_display') else a.appointment_time_slot
            create_notification(
                user=farmer_user,
                title=f"📅 Appointment Scheduled: {crop}",
                message=f"Procurement appointment confirmed for {appt_date_str} ({slot_str}) at {center_name}.",
                notification_type="APPOINTMENT",
                target_url="/appointments/",
                related_object=a,
                event_key=f"appointment_sched_{a.id}",
            )

        # 3. Token & Live Queue Step
        tokens = Token.objects.filter(farmer=farmer_user).select_related("procurement_center", "produce")
        for t in tokens:
            center_name = t.procurement_center.name if t.procurement_center else "Center"
            crop = t.produce.crop_name if t.produce else "Produce"
            create_notification(
                user=farmer_user,
                title=f"🎟️ Digital Token Issued: #{t.token_number}",
                message=f"Token #{t.token_number} issued for {crop} at {center_name}. Counter #{t.counter_number}.",
                notification_type="TOKEN",
                target_url="/tokens/",
                related_object=t,
                event_key=f"token_issued_{t.id}",
            )


        # 4. Pipeline Steps (Gate Entry, Quality Check, Weighbridge, Acceptance, Bill, Payment)
        records = ProcurementRecord.objects.filter(farmer=farmer_user).select_related("bill", "payment_record")
        for r in records:
            stage = r.current_stage

            # Center Assignment step
            if r.center:
                create_notification(
                    user=farmer_user,
                    title=f"🏢 Procurement Center Assigned: {r.center_display_name}",
                    message=f"Center '{r.center_display_name}' assigned for {r.crop_name} procurement.",
                    notification_type="PROCUREMENT",
                    target_url="/procurement/centers/",
                    related_object=r,
                    event_key=f"center_assigned_{r.id}_{r.center.id}",
                )

            # Step 4a: Gate Entry
            if stage in ["GATE_ENTRY", "QUALITY_CHECK", "WEIGHING", "ACCEPTANCE", "BILL_GENERATED", "PAYMENT_INITIATED", "PAYMENT_RECEIVED", "COMPLETED"]:
                create_notification(
                    user=farmer_user,
                    title=f"🚪 Gate Entry Confirmed: #{r.token_number}",
                    message=f"Vehicle arrival confirmed at Mandi Gate for {r.crop_name} (Token #{r.token_number}). Vehicle: {r.vehicle_number or 'Verified'}.",
                    notification_type="TOKEN",
                    target_url="/procurement/status/",
                    related_object=r,
                    event_key=f"stage_gate_{r.id}",
                )

            # Step 4b: Quality Check
            if stage in ["QUALITY_CHECK", "WEIGHING", "ACCEPTANCE", "BILL_GENERATED", "PAYMENT_INITIATED", "PAYMENT_RECEIVED", "COMPLETED"]:
                grade = r.quality_grade or "Standard Grade"
                moisture = r.moisture_content or "11.5%"
                create_notification(
                    user=farmer_user,
                    title=f"🔬 Quality Check Passed: {r.crop_name}",
                    message=f"Quality assessment completed. Grade: {grade}, Moisture: {moisture}. Proceeding to Weighbridge.",
                    notification_type="QUALITY",
                    target_url="/procurement/status/",
                    related_object=r,
                    event_key=f"stage_quality_{r.id}",
                )
            elif stage == "REJECTED" and r.quality_status == "Rejected":
                create_notification(
                    user=farmer_user,
                    title=f"⚠️ Quality Check Failed: {r.crop_name}",
                    message=f"Quality assessment rejected. Reason: {r.rejection_reason or 'Failed standards'}.",
                    notification_type="QUALITY",
                    target_url="/procurement/status/",
                    related_object=r,
                    event_key=f"stage_quality_fail_{r.id}",
                )

            # Step 4c: Weighbridge Scale
            if stage in ["WEIGHING", "ACCEPTANCE", "BILL_GENERATED", "PAYMENT_INITIATED", "PAYMENT_RECEIVED", "COMPLETED"] and r.actual_quantity:
                create_notification(
                    user=farmer_user,
                    title=f"⚖️ Weighing Scale Recorded: {r.actual_quantity} Quintals",
                    message=f"Weighbridge scale recorded. Net Weighed Weight: {r.actual_quantity} Quintals for {r.crop_name}.",
                    notification_type="WEIGHING",
                    target_url="/procurement/status/",
                    related_object=r,
                    event_key=f"stage_weighing_{r.id}",
                )

            # Step 4d: Final Acceptance
            if stage in ["ACCEPTANCE", "BILL_GENERATED", "PAYMENT_INITIATED", "PAYMENT_RECEIVED", "COMPLETED"]:
                create_notification(
                    user=farmer_user,
                    title=f"✅ Produce Accepted for MSP Procurement",
                    message=f"Batch of {r.actual_quantity or r.registered_quantity} Quintals of {r.crop_name} accepted by Officer. Moving to MSP billing.",
                    notification_type="PROCUREMENT",
                    target_url="/procurement/status/",
                    related_object=r,
                    event_key=f"stage_acceptance_{r.id}",
                )

            # Step 4e: MSP Bill Generated
            bill = getattr(r, "bill", None)
            if (stage in ["BILL_GENERATED", "PAYMENT_INITIATED", "PAYMENT_RECEIVED", "COMPLETED"] or bill) and bill:
                create_notification(
                    user=farmer_user,
                    title=f"🧾 MSP Bill Generated: #{bill.bill_number}",
                    message=f"Financial bill #{bill.bill_number} generated. Total Net Payable: ₹{bill.net_amount:,.2f}.",
                    notification_type="BILL",
                    target_url="/payments/",
                    related_object=bill,
                    event_key=f"stage_bill_{r.id}",
                )

            # Step 4f: Direct Bank Transfer Payment
            payment = getattr(r, "payment_record", None)
            if stage in ["PAYMENT_INITIATED", "PAYMENT_RECEIVED", "COMPLETED"] or (payment and payment.payment_status in ["INITIATED", "RECEIVED", "COMPLETED"]):
                amt = bill.net_amount if bill else (r.total_amount or 0.0)
                p_status = "Credit Completed" if (stage in ["PAYMENT_RECEIVED", "COMPLETED"] or (payment and payment.payment_status in ["RECEIVED", "COMPLETED"])) else "Transfer Initiated"
                create_notification(
                    user=farmer_user,
                    title=f"💰 Direct Bank Transfer (DBT): {p_status}",
                    message=f"Payment of ₹{amt:,.2f} {p_status.lower()} via Direct Benefit Transfer for your {r.crop_name} procurement.",
                    notification_type="PAYMENT",
                    target_url="/payments/",
                    related_object=payment or r,
                    event_key=f"stage_payment_{r.id}_{stage}",
                )
    except Exception as e:
        print("Notification sync warning:", e)


