from datetime import date
from django import forms
from produce.models import Produce
from .models import Appointment


class AppointmentBookingForm(forms.Form):
    produce_id = forms.IntegerField(widget=forms.HiddenInput())
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=True,
    )
    appointment_time_slot = forms.ChoiceField(
        choices=Appointment.TIME_SLOT_CHOICES,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_appointment_date(self):
        appt_date = self.cleaned_data.get("appointment_date")
        if appt_date and appt_date < date.today():
            raise forms.ValidationError("Appointment date cannot be in the past.")
        return appt_date

    def clean(self):
        cleaned_data = super().clean()
        produce_id = cleaned_data.get("produce_id")
        appt_date = cleaned_data.get("appointment_date")
        time_slot = cleaned_data.get("appointment_time_slot")

        if not produce_id or not appt_date or not time_slot:
            return cleaned_data

        try:
            produce = Produce.objects.get(pk=produce_id, farmer=self.user)
        except Produce.DoesNotExist:
            raise forms.ValidationError("Invalid produce batch selected.")

        if produce.status == "PROCURED":
            raise forms.ValidationError("Procurement for this produce has already been completed.")

        if produce.status != "REQUESTED":
            raise forms.ValidationError("Procurement must be requested for this produce before booking an appointment.")

        # Check if active appointment already exists
        existing_active = Appointment.objects.filter(
            produce=produce,
            status="CONFIRMED",
        ).exists()
        if existing_active:
            raise forms.ValidationError("An active confirmed appointment already exists for this produce batch.")

        procurement_record = getattr(produce, "procurement_records", None)
        record = produce.procurement_records.first() if procurement_record else None
        if not record or not record.center:
            raise forms.ValidationError("No procurement center has been assigned for this produce request.")

        center = record.center
        booked_count = Appointment.objects.filter(
            procurement_center=center,
            appointment_date=appt_date,
            appointment_time_slot=time_slot,
            status="CONFIRMED",
        ).count()

        if booked_count >= Appointment.SLOT_CAPACITY:
            raise forms.ValidationError(
                f"The time slot '{time_slot}' on {appt_date.strftime('%d %b %Y')} at {center.name} has reached its maximum capacity of {Appointment.SLOT_CAPACITY} appointments. Please select another slot or date."
            )

        cleaned_data["produce_obj"] = produce
        cleaned_data["record_obj"] = record
        cleaned_data["center_obj"] = center
        return cleaned_data
