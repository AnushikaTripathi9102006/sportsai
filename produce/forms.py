from django import forms
from .models import Produce


class ProduceForm(forms.ModelForm):
    class Meta:
        model = Produce
        fields = [
            "crop_name",
            "quantity",
            "unit",
            "harvest_date",
        ]

        widgets = {
            "harvest_date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }