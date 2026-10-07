from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field

from .models import Equipment, RentalRate, Category


class CategoryForm(forms.ModelForm):
    """Form for creating and editing Equipment Category records with Crispy Bootstrap 5."""

    class Meta:
        model = Category
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g. Hydraulic Excavators',
                'class': 'form-control',
                'id': 'id_category_name',
                'autocomplete': 'off',
            }),
            'code': forms.TextInput(attrs={
                'placeholder': 'e.g. EXC (Auto-generated from Name)',
                'class': 'form-control font-monospace text-uppercase',
                'id': 'id_category_code',
                'style': 'text-transform: uppercase;',
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Detailed notes on equipment types included in this category...',
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].required = False  # Allows automatic generation if empty
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='col-12 col-md-8 mb-3'),
                Column('code', css_class='col-12 col-md-4 mb-3'),
            ),
            Row(
                Column('description', css_class='col-12 mb-3'),
            ),
        )

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError(_("Category name is required."))
        qs = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_(f"A category named '{name}' already exists."))
        return name

    def clean_code(self):
        code = self.cleaned_data.get('code', '').upper().strip()
        name = self.cleaned_data.get('name', '').strip()

        if not code and name:
            code = Category.generate_code_from_name(name, existing_pk=self.instance.pk)

        if not code:
            raise forms.ValidationError(_("Category code is required or could not be auto-generated."))

        qs = Category.objects.filter(code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_(f"A category with code '{code}' already exists. Please choose a unique code."))

        return code



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
            'asset_code': forms.TextInput(attrs={
                'class': 'form-control font-monospace text-uppercase',
                'placeholder': 'Auto-generated (e.g. EQ-EXC-CAT-320D-001)',
                'id': 'id_asset_code',
            }),
            'equipment_name': forms.TextInput(attrs={
                'placeholder': 'e.g. Caterpillar 320D Hydraulic Excavator',
                'class': 'form-control',
                'id': 'id_equipment_name',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_category_select',
            }),
            'brand': forms.TextInput(attrs={
                'placeholder': 'e.g. Caterpillar, Komatsu, JCB',
                'class': 'form-control',
                'id': 'id_brand_input',
            }),
            'model_number': forms.TextInput(attrs={
                'placeholder': 'e.g. 320D, PC200-8, JS205',
                'class': 'form-control',
                'id': 'id_model_input',
            }),
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'specifications': forms.HiddenInput(attrs={'id': 'id_specifications_json'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asset_code'].required = False  # Auto-generated if not provided
        self.fields['specifications'].required = False
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
                Field('specifications'),
                css_class='bg-white p-4 rounded-3 border mb-4'
            )
        )


    def clean_asset_code(self):
        asset_code = self.cleaned_data.get('asset_code', '').upper().strip()
        category = self.cleaned_data.get('category')
        brand = self.cleaned_data.get('brand', '').strip()
        model_number = self.cleaned_data.get('model_number', '').strip()

        if not asset_code and category and brand and model_number:
            asset_code = Equipment.generate_asset_code(category, brand, model_number, existing_pk=self.instance.pk)

        if not asset_code:
            raise forms.ValidationError(_("Asset Code is required or could not be auto-generated. Please check Category, Brand, and Model Number."))

        qs = Equipment.objects.filter(asset_code=asset_code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_(f"An equipment asset with code '{asset_code}' already exists."))

        return asset_code

    def clean_specifications(self):
        import json
        specs = self.cleaned_data.get('specifications')
        if not specs:
            return {}
        if isinstance(specs, str):
            try:
                specs = json.loads(specs)
            except (json.JSONDecodeError, TypeError):
                specs = {}
        if isinstance(specs, dict):
            return {str(k).strip(): str(v).strip() for k, v in specs.items() if str(k).strip()}
        return {}




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


RentalRateCreateFormSet = inlineformset_factory(
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

RentalRateUpdateFormSet = inlineformset_factory(
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
    extra=0,
    can_delete=True,
)

# Default alias for backward compatibility
RentalRateFormSet = RentalRateCreateFormSet

