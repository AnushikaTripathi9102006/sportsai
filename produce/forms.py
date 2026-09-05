from django import forms
from .models import Produce, MSPCrop


DEFAULT_MSP_CROPS = [
    ("Paddy (Rice)", "Paddy (Rice)"),
    ("Wheat", "Wheat"),
    ("Jowar (Sorghum)", "Jowar (Sorghum)"),
    ("Bajra (Pearl Millet)", "Bajra (Pearl Millet)"),
    ("Maize", "Maize"),
    ("Ragi (Finger Millet)", "Ragi (Finger Millet)"),
    ("Arhar / Tur (Pigeon Pea)", "Arhar / Tur (Pigeon Pea)"),
    ("Moong (Green Gram)", "Moong (Green Gram)"),
    ("Urad (Black Gram)", "Urad (Black Gram)"),
    ("Gram (Chickpea)", "Gram (Chickpea)"),
    ("Masur (Lentil)", "Masur (Lentil)"),
    ("Groundnut", "Groundnut"),
    ("Sunflower Seed", "Sunflower Seed"),
    ("Soyabean", "Soyabean"),
    ("Sesamum (Til)", "Sesamum (Til)"),
    ("Nigerseed", "Nigerseed"),
    ("Rapeseed & Mustard", "Rapeseed & Mustard"),
    ("Safflower", "Safflower"),
    ("Cotton", "Cotton"),
    ("Copra (De-husked Coconut)", "Copra (De-husked Coconut)"),
    ("Raw Jute", "Raw Jute"),
    ("Sugarcane", "Sugarcane"),
    ("Barley", "Barley"),
]


UP_DISTRICTS = [
    ("Lucknow", "Lucknow"),
    ("Kanpur Nagar", "Kanpur Nagar"),
    ("Sitapur", "Sitapur"),
    ("Ayodhya", "Ayodhya"),
    ("Varanasi", "Varanasi"),
    ("Agra", "Agra"),
    ("Gorakhpur", "Gorakhpur"),
    ("Bareilly", "Bareilly"),
    ("Meerut", "Meerut"),
    ("Prayagraj", "Prayagraj"),
    ("Aligarh", "Aligarh"),
    ("Moradabad", "Moradabad"),
    ("Jhansi", "Jhansi"),
    ("Mathura", "Mathura"),
    ("Basti", "Basti"),
    ("Hardoi", "Hardoi"),
    ("Unnao", "Unnao"),
    ("Barabanki", "Barabanki"),
    ("Rae Bareli", "Rae Bareli"),
    ("Sultanpur", "Sultanpur"),
    ("Lakhimpur Kheri", "Lakhimpur Kheri"),
    ("Shahjahanpur", "Shahjahanpur"),
    ("Ghaziabad", "Ghaziabad"),
    ("Gautam Buddha Nagar", "Gautam Buddha Nagar"),
    ("Bulandshahr", "Bulandshahr"),
    ("Muzaffarnagar", "Muzaffarnagar"),
    ("Saharanpur", "Saharanpur"),
    ("Deoria", "Deoria"),
    ("Azamgarh", "Azamgarh"),
    ("Ghazipur", "Ghazipur"),
    ("Ballia", "Ballia"),
    ("Jaunpur", "Jaunpur"),
    ("Mirzapur", "Mirzapur"),
    ("Banda", "Banda"),
]


class ProduceForm(forms.ModelForm):
    crop_name = forms.ChoiceField(
        label="Crop Name (MSP Mandated)",
        choices=[],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    district = forms.ChoiceField(
        label="District (Uttar Pradesh)",
        choices=UP_DISTRICTS,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Produce
        fields = [
            "crop_name",
            "quantity",
            "unit",
            "harvest_date",
            "district",
            "address",
        ]

        labels = {
            "district": "District (Uttar Pradesh)",
            "address": "Farm / Village Address",
        }

        widgets = {
            "harvest_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "address": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Enter village, landmark, block, or PIN code",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        crop_choices = [("", "-- Select MSP Crop --")]
        try:
            db_crops = MSPCrop.objects.filter(is_active=True).values_list("name", "name")
            if db_crops.exists():
                crop_choices.extend(list(db_crops))
            else:
                crop_choices.extend(DEFAULT_MSP_CROPS)
        except Exception:
            crop_choices.extend(DEFAULT_MSP_CROPS)

        self.fields["crop_name"].choices = crop_choices