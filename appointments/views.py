from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from procurement.models import ProcurementRecord
from procurement.services import sync_all_farmer_procurements


@login_required
def appointments(request):
    sync_all_farmer_procurements()
    records = ProcurementRecord.objects.filter(farmer=request.user).order_by("-created_at")
    active_record = records.first()
    return render(
        request,
        "appointments/appointments.html",
        {
            "records": records,
            "active_record": active_record,
        },
    )


@login_required
def appointment_detail(request):
    return render(request, "appointments/detail.html")


@login_required
def book_appointment(request):
    return render(request, "appointments/book.html")
