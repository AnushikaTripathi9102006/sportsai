from django import forms
from .models import QualityAssessment, WeighingRecord, ProcurementBill, PaymentRecord, ProcurementRecord


class GateEntryForm(forms.Form):
    vehicle_number = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. UP 32 AB 1234',
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional arrival notes...',
        })
    )


class QualityCheckForm(forms.ModelForm):
    IS_PASSED_CHOICES = [
        (True, 'PASS - Meets standards'),
        (False, 'REJECT - Substandard quality'),
    ]

    is_passed = forms.TypedChoiceField(
        choices=IS_PASSED_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        coerce=lambda x: x == 'True' or x is True
    )

    class Meta:
        model = QualityAssessment
        fields = ['quality_grade', 'moisture_percentage', 'foreign_matter_percentage', 'is_passed', 'remarks']
        widgets = {
            'quality_grade': forms.Select(attrs={'class': 'form-control'}),
            'moisture_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'foreign_matter_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Inspection notes/observations'}),
        }


class WeighingForm(forms.ModelForm):
    class Meta:
        model = WeighingRecord
        fields = ['gross_weight', 'tare_weight', 'remarks']
        widgets = {
            'gross_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'Gross Weight (Kg)'}),
            'tare_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'Tare Weight (Kg)'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Weighing notes (optional)'}),
        }

    def clean(self):
        cleaned_data = super().clean() or {}
        gross = cleaned_data.get('gross_weight')
        tare = cleaned_data.get('tare_weight')
        if gross is not None and tare is not None:
            if tare >= gross:
                raise forms.ValidationError("Tare weight cannot be greater than or equal to gross weight.")
        return cleaned_data


class AcceptanceForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[
            ('ACCEPT', 'ACCEPT - Finalize procurement batch'),
            ('REJECT', 'REJECT - Reject procurement batch'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Final acceptance remarks...'})
    )


class BillGenerationForm(forms.Form):
    rate_per_quintal = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'MSP Rate (₹/Quintal)'})
    )
    deductions = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        initial=0.00,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'Deductions (₹)'})
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Bill calculation notes...'})
    )


class PaymentInitiationForm(forms.Form):
    payment_mode = forms.CharField(
        max_length=50,
        initial="Bank Transfer / DBT",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bank Transfer / DBT'})
    )
    transaction_reference = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction Ref / UTR No.'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Payment initiation details...'})
    )



class PaymentReceivedForm(forms.Form):
    confirmation_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Farmer payment confirmation notes...'})
    )
