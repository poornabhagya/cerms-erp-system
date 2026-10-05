from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field

from .models import Equipment, RentalRate, Category


class EquipmentForm(forms.ModelForm):
    """Form for creating and editing Equipment Master asset records with Crispy Bootstrap 5."""

    class Meta:
        model = Equipment
        fields = [
            'asset_code',
            'equipment_name',
            'category',
            'brand',
            'model_number',
            'serial_number',
            'manufacture_year',
            'purchase_cost',
            'purchase_date',
            'current_hour_meter',
            'status',
            'primary_image',
            'specifications',
        ]
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'specifications': forms.Textarea(attrs={'rows': 3, 'placeholder': '{"Operating Weight": "22 Ton", "Engine Power": "150 HP"}'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False  # Allows enclosing in an overarching form for inline formsets
        self.helper.layout = Layout(
            Div(
                Row(
                    Column('asset_code', css_class='col-12 col-md-4 mb-3'),
                    Column('equipment_name', css_class='col-12 col-md-8 mb-3'),
                ),
                Row(
                    Column('category', css_class='col-12 col-md-4 mb-3'),
                    Column('brand', css_class='col-12 col-md-4 mb-3'),
                    Column('model_number', css_class='col-12 col-md-4 mb-3'),
                ),
                Row(
                    Column('serial_number', css_class='col-12 col-md-6 mb-3'),
                    Column('manufacture_year', css_class='col-12 col-md-6 mb-3'),
                ),
                Row(
                    Column('purchase_cost', css_class='col-12 col-md-6 mb-3'),
                    Column('purchase_date', css_class='col-12 col-md-6 mb-3'),
                ),
                Row(
                    Column('current_hour_meter', css_class='col-12 col-md-6 mb-3'),
                    Column('status', css_class='col-12 col-md-6 mb-3'),
                ),
                Row(
                    Column('primary_image', css_class='col-12 mb-3'),
                ),
                Row(
                    Column('specifications', css_class='col-12 mb-3'),
                ),
                css_class='bg-white p-4 rounded-3 border mb-4'
            )
        )


class RentalRateForm(forms.ModelForm):
    """Form for inline rental rate management."""

    class Meta:
        model = RentalRate
        fields = [
            'daily_rate',
            'hourly_rate',
            'weekly_rate',
            'monthly_rate',
            'overtime_hourly_rate',
            'minimum_rental_hours',
            'effective_from',
            'is_active',
        ]
        widgets = {
            'effective_from': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }


RentalRateFormSet = inlineformset_factory(
    Equipment,
    RentalRate,
    form=RentalRateForm,
    fields=[
        'daily_rate',
        'hourly_rate',
        'weekly_rate',
        'monthly_rate',
        'overtime_hourly_rate',
        'minimum_rental_hours',
        'effective_from',
        'is_active',
    ],
    extra=1,
    can_delete=True,
)
