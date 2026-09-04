from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def appointments(request):
	return render(request, "appointments/appointments.html")


@login_required
def appointment_detail(request):
	return render(request, "appointments/detail.html")


@login_required
def book_appointment(request):
	return render(request, "appointments/book.html")
