import uuid
from django.db import transaction
from django.utils import timezone
from .models import (
    ProcurementRecord,
    QualityAssessment,
    WeighingRecord,
    ProcurementBill,
    PaymentRecord,
    ProcurementAuditLog,
)
from produce.models import Produce
from .models import ProcurementCenter


def sync_all_farmer_procurements():
    """
    Sync all registered farmer produce records to ProcurementRecord
    so that every procurement request is 100% visible on the Officer Dashboard.
    """
    produces = Produce.objects.all()
    for produce in produces:
        center = (
            ProcurementCenter.objects.filter(district__iexact=produce.district).first()
            or ProcurementCenter.objects.filter(is_active=True).first()
        )
        record, created = ProcurementRecord.objects.get_or_create(
            produce=produce,
            defaults={
                "farmer": produce.farmer,
                "crop_name": produce.crop_name,
                "registered_quantity": produce.quantity,
                "unit": produce.get_unit_display() or "Quintals",
                "center": center,
                "center_name": center.name if center else "Procurement Center",
                "current_stage": "APPOINTMENT" if produce.status == "REQUESTED" else "REGISTRATION",
                "appointment_date": "Today, 10:00 AM",
                "token_number": f"TK-{produce.id:04d}",
            },
        )
        if not created:
            if record.center is None and center:
                record.center = center
            if produce.status == "REQUESTED" and record.current_stage == "REGISTRATION":
                record.current_stage = "APPOINTMENT"
            record.save()




VALID_TRANSITIONS = {
    "REGISTRATION": ["APPOINTMENT", "GATE_ENTRY", "CANCELLED"],
    "APPOINTMENT": ["GATE_ENTRY", "CANCELLED"],
    "GATE_ENTRY": ["QUALITY_CHECK", "REJECTED", "CANCELLED"],
    "QUALITY_CHECK": ["WEIGHING", "REJECTED"],
    "WEIGHING": ["ACCEPTANCE", "BILL_GENERATED", "REJECTED"],
    "ACCEPTANCE": ["BILL_GENERATED", "REJECTED"],
    "BILL_GENERATED": ["PAYMENT_INITIATED"],
    "PAYMENT_INITIATED": ["PAYMENT_RECEIVED"],
    "PAYMENT_RECEIVED": ["COMPLETED"],
    "COMPLETED": [],
    "REJECTED": [],
    "CANCELLED": [],
}


def create_audit_log(actor, action, record=None, center=None, details=""):
    """Creates a permanent non-deletable audit log entry."""
    return ProcurementAuditLog.objects.create(
        actor=actor,
        action=action,
        procurement_record=record,
        center=center or (record.center if record else None),
        details=details,
    )


def transition_procurement_stage(actor, record, target_stage, details=""):
    """
    Validates and executes a procurement status transition atomically.
    Raises ValueError if transition is invalid.
    """
    with transaction.atomic():
        current_stage = record.current_stage
        allowed = VALID_TRANSITIONS.get(current_stage, [])

        if target_stage not in allowed:
            raise ValueError(
                f"Invalid transition: Cannot move procurement #{record.id} from {current_stage} to {target_stage}."
            )

        record.current_stage = target_stage
        record.save()

        create_audit_log(
            actor=actor,
            action=f"STAGE_TRANSITION: {current_stage} -> {target_stage}",
            record=record,
            center=record.center,
            details=details or f"Stage updated to {target_stage} by {actor.username}",
        )
        return record


def perform_gate_entry(officer, record, vehicle_number="", notes=""):
    """Marks farmer arrival and gate entry."""
    with transaction.atomic():
        if vehicle_number:
            record.vehicle_number = vehicle_number
        record.is_identity_verified = True
        record.is_produce_verified = True
        record.is_request_verified = True
        record.verified_by = officer.get_full_name() or officer.username
        record.gate_entry_at = timezone.now()
        record.save()

        details_msg = f"Gate entry completed by {officer.username}"
        if vehicle_number:
            details_msg += f" (Vehicle: {vehicle_number})"
        if notes:
            details_msg += f" - Notes: {notes}"

        transition_procurement_stage(
            actor=officer,
            record=record,
            target_stage="GATE_ENTRY",
            details=details_msg,
        )
        return record


def perform_quality_check(
    officer,
    record,
    result,
    quality_grade="GRADE_A",
    moisture_percentage=11.50,
    foreign_matter_percentage=1.00,
    damaged_percentage=0.50,
    rejection_reason="",
    remarks="",
):
    """Records quality inspection results."""
    with transaction.atomic():
        # First transition to QUALITY_CHECK if coming from GATE_ENTRY
        if record.current_stage == "GATE_ENTRY":
            transition_procurement_stage(officer, record, "QUALITY_CHECK")

        quality, _ = QualityAssessment.objects.update_or_create(
            procurement_record=record,
            defaults={
                "officer": officer,
                "quality_grade": quality_grade,
                "moisture_percentage": moisture_percentage,
                "foreign_matter_percentage": foreign_matter_percentage,
                "damaged_percentage": damaged_percentage,
                "result": result,
                "rejection_reason": rejection_reason if result == "REJECTED" else "",
                "remarks": remarks,
            },
        )

        record.quality_grade = quality.get_quality_grade_display()
        record.moisture_content = f"{moisture_percentage}%"
        record.quality_status = "Passed" if result == "PASSED" else "Rejected"
        record.officer_remarks = remarks
        record.save()

        if result == "REJECTED":
            record.rejection_reason = rejection_reason
            transition_procurement_stage(
                actor=officer,
                record=record,
                target_stage="REJECTED",
                details=f"Quality inspection failed: {rejection_reason}",
            )
        else:
            transition_procurement_stage(
                actor=officer,
                record=record,
                target_stage="WEIGHING",
                details=f"Quality inspection passed ({quality_grade})",
            )

        return quality


def perform_weighing(officer, record, gross_weight, tare_weight, remarks=""):
    """Validates and records gross, tare, and net weights."""
    with transaction.atomic():
        gross = float(gross_weight)
        tare = float(tare_weight)

        if gross <= 0:
            raise ValueError("Gross weight must be greater than zero.")
        if tare < 0:
            raise ValueError("Tare weight cannot be negative.")
        if tare >= gross:
            raise ValueError("Tare weight must be less than gross weight.")

        net = round(gross - tare, 2)

        weighing, _ = WeighingRecord.objects.update_or_create(
            procurement_record=record,
            defaults={
                "officer": officer,
                "gross_weight": gross,
                "tare_weight": tare,
                "net_weight": net,
                "unit": record.unit,
                "remarks": remarks,
            },
        )

        record.actual_quantity = net
        record.save()

        transition_procurement_stage(
            actor=officer,
            record=record,
            target_stage="ACCEPTANCE",
            details=f"Weighing recorded: Gross={gross}, Tare={tare}, Net={net}",
        )
        return weighing


def perform_acceptance(officer, record, decision, rejection_reason=""):
    """Final officer acceptance or rejection decision."""
    with transaction.atomic():
        if decision == "REJECT":
            if not rejection_reason:
                raise ValueError("Rejection reason is required.")
            record.rejection_reason = rejection_reason
            transition_procurement_stage(
                actor=officer,
                record=record,
                target_stage="REJECTED",
                details=f"Procurement rejected at acceptance: {rejection_reason}",
            )
        else:
            if record.current_stage == "WEIGHING":
                transition_procurement_stage(
                    actor=officer,
                    record=record,
                    target_stage="ACCEPTANCE",
                    details=f"Procurement accepted by {officer.username}",
                )
        return record


def perform_bill_generation(officer, record, rate_per_quintal=2275.00, deductions=0.00):
    """Generates financial bill for accepted procurement."""
    with transaction.atomic():
        if hasattr(record, "bill"):
            return record.bill

        quantity = float(record.actual_quantity or record.registered_quantity)
        rate = float(rate_per_quintal)
        ded = float(deductions)

        gross_amt = round(quantity * rate, 2)
        net_amt = round(gross_amt - ded, 2)

        bill_no = f"BILL-UP-{record.id:04d}-{uuid.uuid4().hex[:4].upper()}"

        bill = ProcurementBill.objects.create(
            bill_number=bill_no,
            procurement_record=record,
            quantity_quintals=quantity,
            rate_per_quintal=rate,
            gross_amount=gross_amt,
            deductions=ded,
            net_amount=net_amt,
            generated_by=officer,
        )

        record.rate_per_unit = rate
        record.total_amount = net_amt
        record.save()

        # Pre-create payment record
        PaymentRecord.objects.get_or_create(
            procurement_record=record,
            bill=bill,
            defaults={"payment_status": "PENDING"},
        )

        transition_procurement_stage(
            actor=officer,
            record=record,
            target_stage="BILL_GENERATED",
            details=f"Bill #{bill_no} generated for ₹{net_amt}",
        )
        return bill


def perform_payment_initiation(officer, record, transaction_reference=""):
    """Initiates payment for a generated bill."""
    with transaction.atomic():
        if not hasattr(record, "bill"):
            raise ValueError("Cannot initiate payment before bill generation.")

        if record.current_stage != "BILL_GENERATED":
            raise ValueError(f"Cannot initiate payment from stage {record.current_stage}.")

        payment, _ = PaymentRecord.objects.get_or_create(
            procurement_record=record,
            bill=record.bill,
        )

        ref_no = transaction_reference or f"TXN-UP-{record.id:04d}-{uuid.uuid4().hex[:6].upper()}"
        payment.payment_status = "INITIATED"
        payment.transaction_reference = ref_no
        payment.initiated_by = officer
        payment.initiated_at = timezone.now()
        payment.save()

        record.payment_status = "Initiated"
        transition_procurement_stage(
            actor=officer,
            record=record,
            target_stage="PAYMENT_INITIATED",
            details=f"Payment initiated. Txn Ref: {ref_no}",
        )
        return payment


def perform_payment_received(officer, record):
    """Confirms payment completion."""
    with transaction.atomic():
        if not hasattr(record, "payment_record"):
            raise ValueError("No payment record found.")

        payment = record.payment_record
        payment.payment_status = "RECEIVED"
        payment.confirmed_at = timezone.now()
        payment.save()

        record.payment_status = "Completed"
        transition_procurement_stage(
            actor=officer,
            record=record,
            target_stage="PAYMENT_RECEIVED",
            details="Payment received and verified.",
        )

        # Final completion
        transition_procurement_stage(
            actor=officer,
            record=record,
            target_stage="COMPLETED",
            details="Procurement workflow successfully completed.",
        )

        if record.produce:
            record.produce.status = "PROCURED"
            record.produce.save()

        return payment
