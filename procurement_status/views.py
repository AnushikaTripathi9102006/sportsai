from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from produce.models import Produce
from procurement.models import ProcurementRecord
from procurement.services import sync_all_farmer_procurements

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
def procurement_status(request):
    profile = getattr(request.user, "profile", None)
    sync_all_farmer_procurements()

    procurement_records = ProcurementRecord.objects.filter(farmer=request.user).order_by("-created_at")
    procurement_record = procurement_records.first()

    produce_list = Produce.objects.filter(farmer=request.user).order_by("-created_at")
    active_produce = produce_list.filter(status="REQUESTED").first() or produce_list.first()

    if procurement_record:
        stage = procurement_record.current_stage
        stage_rank = STAGE_RANKS.get(stage, 1)

        crop_name = procurement_record.crop_name
        registered_qty = float(procurement_record.registered_quantity)
        actual_qty = float(procurement_record.actual_quantity) if procurement_record.actual_quantity is not None else None
        diff_qty = round(actual_qty - registered_qty, 2) if actual_qty is not None else None

        unit = procurement_record.unit
        center_name = procurement_record.center_name or (procurement_record.center.name if procurement_record.center else "Procurement Center")
        token_number = procurement_record.token_number
        appointment_time = procurement_record.appointment_date

        if stage == "COMPLETED":
            overall_status = "Procurement Completed"
        elif stage == "REJECTED":
            overall_status = "Procurement Rejected"
        elif stage == "CANCELLED":
            overall_status = "Procurement Cancelled"
        else:
            overall_status = f"Status: {procurement_record.get_current_stage_display()}"

        verification_status = "Completed" if stage_rank >= 3 else "Pending"
        verified_by = procurement_record.verified_by or "Procurement Officer"

        quality_assessment = getattr(procurement_record, "quality_assessment", None)
        if quality_assessment:
            quality_status = quality_assessment.get_result_display()
            quality_grade = quality_assessment.get_quality_grade_display()
            moisture_content = f"{quality_assessment.moisture_percentage}%"
            officer_remarks = quality_assessment.remarks or procurement_record.officer_remarks or "Quality inspection completed."
        else:
            quality_status = procurement_record.quality_status
            quality_grade = procurement_record.quality_grade
            moisture_content = procurement_record.moisture_content
            officer_remarks = procurement_record.officer_remarks or "Quality inspection pending."

        bill = getattr(procurement_record, "bill", None)
        rate_per_quintal = float(bill.rate_per_quintal) if bill else float(procurement_record.rate_per_unit)
        total_amount = float(bill.net_amount) if bill else float(procurement_record.total_amount or (registered_qty * rate_per_quintal))

        payment_record = getattr(procurement_record, "payment_record", None)
        if payment_record:
            payment_status = payment_record.get_payment_status_display()
        else:
            payment_status = procurement_record.payment_status

        procurement_data = {
            "id": procurement_record.id,
            "crop_name": crop_name,
            "registered_qty": registered_qty,
            "actual_qty": actual_qty,
            "diff_qty": diff_qty,
            "unit": unit,
            "center_name": center_name,
            "counter_number": procurement_record.counter_number,
            "token_number": token_number,
            "appointment_time": appointment_time,
            "current_stage": stage,
            "stage_rank": stage_rank,
            "stage_title": procurement_record.get_current_stage_display(),
            "overall_status": overall_status,
            "verification_status": verification_status,
            "verified_by": verified_by,
            "quality_status": quality_status,
            "quality_grade": quality_grade,
            "moisture_content": moisture_content,
            "officer_remarks": officer_remarks,
            "rejection_reason": procurement_record.rejection_reason,
            "rate_per_quintal": rate_per_quintal,
            "total_amount": total_amount,
            "payment_status": payment_status,
        }
    else:
        procurement_data = None

    history_records = procurement_records.filter(current_stage="COMPLETED")
    procurement_history = [
        {
            "date": rec.updated_at.strftime("%d %b %Y"),
            "crop": rec.crop_name,
            "quantity": f"{rec.actual_quantity or rec.registered_quantity} {rec.unit}",
            "center": rec.center_name or (rec.center.name if rec.center else "Procurement Center"),
            "amount": f"₹{rec.total_amount:,.2f}",
            "status": "Completed",
        }
        for rec in history_records
    ]

    return render(
        request,
        "procurement_status/status.html",
        {
            "farmer": request.user,
            "profile": profile,
            "active_produce": active_produce,
            "procurement": procurement_data,
            "procurement_record": procurement_record,
            "procurement_history": procurement_history,
        },
    )


@login_required
def procurement_detail(request):
    profile = getattr(request.user, "profile", None)
    sync_all_farmer_procurements()

    procurement_records = ProcurementRecord.objects.filter(farmer=request.user).order_by("-created_at")
    procurement_record = procurement_records.first()

    produce_list = Produce.objects.filter(farmer=request.user).order_by("-created_at")
    active_produce = produce_list.filter(status="REQUESTED").first() or produce_list.first()

    if procurement_record:
        stage = procurement_record.current_stage
        stage_rank = STAGE_RANKS.get(stage, 1)

        registered_qty = float(procurement_record.registered_quantity)
        actual_qty = float(procurement_record.actual_quantity) if procurement_record.actual_quantity is not None else None
        diff_qty = round(actual_qty - registered_qty, 2) if actual_qty is not None else None

        bill = getattr(procurement_record, "bill", None)
        rate_per_quintal = float(bill.rate_per_quintal) if bill else float(procurement_record.rate_per_unit)
        total_amount = float(bill.net_amount) if bill else float(procurement_record.total_amount or (registered_qty * rate_per_quintal))

        payment_record = getattr(procurement_record, "payment_record", None)
        payment_status = payment_record.get_payment_status_display() if payment_record else procurement_record.payment_status

        procurement_data = {
            "crop_name": procurement_record.crop_name,
            "registered_qty": registered_qty,
            "actual_qty": actual_qty,
            "diff_qty": diff_qty,
            "unit": procurement_record.unit,
            "harvest_date": procurement_record.created_at.strftime("%d %b %Y"),
            "center_name": procurement_record.center_name or (procurement_record.center.name if procurement_record.center else "Procurement Center"),
            "counter_number": procurement_record.counter_number,
            "token_number": procurement_record.token_number,
            "appointment_time": procurement_record.appointment_date,
            "verified_by": procurement_record.verified_by or "Officer R. Sharma",
            "quality_grade": procurement_record.quality_grade,
            "moisture_content": procurement_record.moisture_content,
            "officer_remarks": procurement_record.officer_remarks or "Produce meets procurement standards.",
            "rate_per_quintal": rate_per_quintal,
            "total_amount": total_amount,
            "payment_status": payment_status,
            "stage_rank": stage_rank,
            "stage_title": procurement_record.get_current_stage_display(),
        }

        timeline_items = [
            {"stage": "Produce Registered", "timestamp": procurement_record.created_at.strftime("%d %b %Y, %I:%M %p"), "status": "done" if stage_rank > 1 else ("current" if stage_rank == 1 else "pending")},
            {"stage": "Appointment Confirmed", "timestamp": procurement_record.appointment_date, "status": "done" if stage_rank > 2 else ("current" if stage_rank == 2 else "pending")},
            {"stage": "Farmer Arrived", "timestamp": procurement_record.gate_entry_at.strftime("%d %b %Y, %I:%M %p") if procurement_record.gate_entry_at else ("Done" if stage_rank > 3 else ("Current" if stage_rank == 3 else "Pending")), "status": "done" if stage_rank > 3 else ("current" if stage_rank == 3 else "pending")},
            {"stage": "Verification Completed", "timestamp": "Completed" if stage_rank >= 3 else "Pending", "status": "done" if stage_rank > 3 else ("current" if stage_rank == 3 else "pending")},
            {"stage": f"Quality Inspection ({procurement_record.quality_grade})", "timestamp": "Passed" if stage_rank >= 5 else "Pending", "status": "done" if stage_rank > 4 else ("current" if stage_rank == 4 else "pending")},
            {"stage": f"Weighing Recorded ({actual_qty or registered_qty} {procurement_record.unit})", "timestamp": "Recorded" if stage_rank >= 5 else "Pending", "status": "done" if stage_rank > 5 else ("current" if stage_rank == 5 else "pending")},
            {"stage": "Officer Acceptance & Bill Generated", "timestamp": "Generated" if stage_rank >= 7 else "Pending", "status": "done" if stage_rank > 7 else ("current" if stage_rank in [6, 7] else "pending")},
            {"stage": "Payment Processing", "timestamp": payment_status, "status": "done" if stage_rank > 8 else ("current" if stage_rank == 8 else "pending")},
            {"stage": "Payment Completed", "timestamp": "Completed" if stage_rank >= 10 else "Pending", "status": "done" if stage_rank == 10 else "pending"},
        ]
    else:
        procurement_data = None
        timeline_items = []

    return render(
        request,
        "procurement_status/detail.html",
        {
            "farmer": request.user,
            "profile": profile,
            "active_produce": active_produce,
            "procurement": procurement_data,
            "procurement_record": procurement_record,
            "timeline": timeline_items,
        },
    )
