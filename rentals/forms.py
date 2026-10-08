from decimal import Decimal
from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field

from fleet.models import Equipment
from .models import Customer, ProjectSite, Quotation, QuotationItem, RentalContract, RentalContractItem, DispatchReturn


class CustomerForm(forms.ModelForm):
    """
    Form for registering and updating Customer commercial master records with Crispy Bootstrap 5 styling.
    """
    customer_code = forms.CharField(
        label=_("Customer Code"),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Auto-generated (e.g. CUST-2026-001)',
            'readonly': 'readonly',
            'class': 'form-control bg-light font-monospace fw-semibold text-primary',
        }),
        help_text=_("System auto-generated identifier (CUST-YYYY-XXX).")
    )

    class Meta:
        model = Customer
        fields = [
            'customer_code',
            'company_name',
            'contact_person',
            'phone',
            'email',
            'billing_address',
            'vat_tax_number',
            'credit_limit',
            'current_outstanding_balance',
            'status',
        ]
        widgets = {
            'billing_address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter full legal and billing address...'}),
            'credit_limit': forms.NumberInput(attrs={'step': '1000.00', 'min': '0'}),
            'current_outstanding_balance': forms.NumberInput(attrs={'step': '100.00', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            if not self.initial.get('customer_code'):
                self.initial['customer_code'] = Customer.generate_customer_code()
            self.fields['customer_code'].widget.attrs['readonly'] = True
            self.fields['customer_code'].widget.attrs['class'] = 'form-control bg-light font-monospace fw-semibold text-primary'
        else:
            self.fields['customer_code'].widget.attrs['readonly'] = True
            self.fields['customer_code'].widget.attrs['class'] = 'form-control bg-light font-monospace'

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                HTML('<h5 class="fw-bold mb-3 text-dark"><i class="bi bi-building me-2 text-primary"></i> Corporate & Contact Information</h5>'),
                Row(
                    Column('customer_code', css_class='col-12 col-md-4 mb-3'),
                    Column('company_name', css_class='col-12 col-md-8 mb-3'),
                ),
                Row(
                    Column('contact_person', css_class='col-12 col-md-4 mb-3'),
                    Column('phone', css_class='col-12 col-md-4 mb-3'),
                    Column('email', css_class='col-12 col-md-4 mb-3'),
                ),
                Row(
                    Column('billing_address', css_class='col-12 col-md-8 mb-3'),
                    Column('vat_tax_number', css_class='col-12 col-md-4 mb-3'),
                ),
                css_class='bg-white p-4 rounded-3 border shadow-sm mb-4'
            ),
            Div(
                HTML('<h5 class="fw-bold mb-3 text-dark"><i class="bi bi-wallet2 me-2 text-success"></i> Credit & Financial Standing</h5>'),
                Row(
                    Column('credit_limit', css_class='col-12 col-md-4 mb-3'),
                    Column('current_outstanding_balance', css_class='col-12 col-md-4 mb-3'),
                    Column('status', css_class='col-12 col-md-4 mb-3'),
                ),
                HTML('''
                <div class="alert alert-info d-flex align-items-center mb-0 mt-2 py-2" role="alert">
                    <i class="bi bi-info-circle-fill me-2 fs-5"></i>
                    <small>Customer credit exposure is automatically evaluated during Quotation creation and Contract signing. Accounts marked as <strong>Blocked</strong> cannot issue new rental orders.</small>
                </div>
                '''),
                css_class='bg-white p-4 rounded-3 border shadow-sm mb-4'
            )
        )

    def clean_customer_code(self):
        code = self.cleaned_data.get('customer_code')
        if not code:
            code = Customer.generate_customer_code(existing_pk=self.instance.pk)
        return code


class ProjectSiteForm(forms.ModelForm):
    """
    Form for registering and updating physical Project Sites linked to Customer organizations.
    """
    project_code = forms.CharField(
        label=_("Project Site Code"),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Auto-generated (e.g. PRJ-001-01)',
            'readonly': 'readonly',
            'class': 'form-control bg-light font-monospace fw-semibold text-success',
        }),
        help_text=_("System auto-generated identifier (PRJ-[Customer_Sequence]-[Site_Sequence]).")
    )

    class Meta:
        model = ProjectSite
        fields = [
            'project_code',
            'customer',
            'project_name',
            'site_address',
            'gps_coordinates',
            'site_contact_person',
            'site_contact_phone',
            'status',
        ]
        widgets = {
            'site_address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Detailed physical location, access road, landmarks...'}),
            'gps_coordinates': forms.TextInput(attrs={'placeholder': 'e.g. 6.9271,79.8612 (Latitude, Longitude)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            initial_customer = self.initial.get('customer')
            if initial_customer and not self.initial.get('project_code'):
                self.initial['project_code'] = ProjectSite.generate_project_code(customer=initial_customer)
            self.fields['project_code'].widget.attrs['readonly'] = True
            self.fields['project_code'].widget.attrs['class'] = 'form-control bg-light font-monospace fw-semibold text-success'
        else:
            self.fields['project_code'].widget.attrs['readonly'] = True
            self.fields['project_code'].widget.attrs['class'] = 'form-control bg-light font-monospace'

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                HTML('<h5 class="fw-bold mb-3 text-dark"><i class="bi bi-geo-alt me-2 text-primary"></i> Site Location & Ownership</h5>'),
                Row(
                    Column('project_code', css_class='col-12 col-md-4 mb-3'),
                    Column('customer', css_class='col-12 col-md-8 mb-3'),
                ),
                Row(
                    Column('project_name', css_class='col-12 col-md-8 mb-3'),
                    Column('status', css_class='col-12 col-md-4 mb-3'),
                ),
                Row(
                    Column('site_address', css_class='col-12 col-md-8 mb-3'),
                    Column('gps_coordinates', css_class='col-12 col-md-4 mb-3'),
                ),
                css_class='bg-white p-4 rounded-3 border shadow-sm mb-4'
            ),
            Div(
                HTML('<h5 class="fw-bold mb-3 text-dark"><i class="bi bi-person-badge me-2 text-info"></i> Resident Site Supervisor / Receiving Officer</h5>'),
                Row(
                    Column('site_contact_person', css_class='col-12 col-md-6 mb-3'),
                    Column('site_contact_phone', css_class='col-12 col-md-6 mb-3'),
                ),
                css_class='bg-white p-4 rounded-3 border shadow-sm mb-4'
            )
        )

    def clean_project_code(self):
        code = self.cleaned_data.get('project_code')
        customer = self.cleaned_data.get('customer') or self.data.get('customer')
        if not code:
            code = ProjectSite.generate_project_code(customer=customer, existing_pk=self.instance.pk)
        return code


class QuotationForm(forms.ModelForm):
    """
    Form for building commercial quotations with dynamic multi-asset pricing,
    transport, discount, and statutory tax calculations.
    """
    quotation_no = forms.CharField(
        label=_("Quotation Number"),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Auto-generated (e.g. QT-2026-0001)',
            'readonly': 'readonly',
            'class': 'form-control bg-light font-monospace fw-semibold text-primary',
            'id': 'id_quotation_no',
        }),
        help_text=_("System auto-generated identifier (QT-YYYY-XXXX).")
    )
    subtotal_amount = forms.DecimalField(
        label=_("Base Tariff / Subtotal Amount (LKR)"),
        required=False,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'id': 'id_subtotal', 'class': 'form-control bg-light font-monospace fw-bold', 'readonly': 'readonly'}),
        help_text=_("Sum of all equipment line item subtotals.")
    )
    total_tax_amount = forms.DecimalField(
        label=_("Total Tax Amount (18% VAT) (LKR)"),
        required=False,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'id': 'id_tax_amount', 'class': 'form-control bg-light font-monospace', 'readonly': 'readonly'}),
    )
    grand_total_amount = forms.DecimalField(
        label=_("Grand Total Amount (LKR)"),
        required=False,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'id': 'id_grand_total', 'class': 'form-control bg-light font-monospace fw-bold fs-5 text-success', 'readonly': 'readonly'}),
    )

    class Meta:
        model = Quotation
        fields = [
            'quotation_no',
            'customer',
            'project_site',
            'start_date',
            'end_date',
            'rate_type',
            'estimated_transport_cost',
            'security_deposit_required',
            'discount_percentage',
            'subtotal_amount',
            'total_tax_amount',
            'grand_total_amount',
            'status',
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select', 'id': 'id_customer'}),
            'project_site': forms.Select(attrs={'class': 'form-select', 'id': 'id_project_site'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_start_date'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_end_date'}),
            'rate_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_rate_type'}),
            'estimated_transport_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'form-control font-monospace', 'id': 'id_transport_cost', 'placeholder': '0.00'}),
            'security_deposit_required': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'form-control font-monospace', 'id': 'id_deposit_required', 'placeholder': '0.00'}),
            'discount_percentage': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100', 'class': 'form-control font-monospace', 'id': 'id_discount_pct', 'placeholder': '0.00'}),
            'status': forms.Select(attrs={'class': 'form-select', 'id': 'id_status'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            if not self.initial.get('quotation_no'):
                self.initial['quotation_no'] = Quotation.generate_quotation_no()
            self.fields['quotation_no'].widget.attrs['readonly'] = True
            self.fields['quotation_no'].widget.attrs['class'] = 'form-control bg-light font-monospace fw-semibold text-primary'
        else:
            self.fields['quotation_no'].widget.attrs['readonly'] = True
            self.fields['quotation_no'].widget.attrs['class'] = 'form-control bg-light font-monospace'

        # Ensure all widgets have standard Bootstrap form classes
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            else:
                existing_class = field.widget.attrs.get('class', '')
                if 'form-control' not in existing_class and 'form-select' not in existing_class:
                    field.widget.attrs['class'] = f"form-control {existing_class}".strip()

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                HTML('<h5 class="fw-bold mb-3 text-dark"><i class="bi bi-file-earmark-text me-2 text-primary"></i> Quotation Scope & Scheduling</h5>'),
                Row(
                    Column('quotation_no', css_class='col-12 col-md-4 mb-3'),
                    Column('customer', css_class='col-12 col-md-4 mb-3'),
                    Column('project_site', css_class='col-12 col-md-4 mb-3'),
                ),
                Row(
                    Column('start_date', css_class='col-12 col-md-4 mb-3'),
                    Column('end_date', css_class='col-12 col-md-4 mb-3'),
                    Column('rate_type', css_class='col-12 col-md-4 mb-3'),
                ),
                css_class='bg-white p-4 rounded-3 border shadow-sm mb-4'
            ),
            Div(
                HTML('<h5 class="fw-bold mb-3 text-dark"><i class="bi bi-cash-stack me-2 text-success"></i> Commercial Pricing & Deposit Terms</h5>'),
                Row(
                    Column('estimated_transport_cost', css_class='col-12 col-md-4 mb-3'),
                    Column('security_deposit_required', css_class='col-12 col-md-4 mb-3'),
                    Column('discount_percentage', css_class='col-12 col-md-4 mb-3'),
                ),
                Row(
                    Column('subtotal_amount', css_class='col-12 col-md-4 mb-3'),
                    Column('total_tax_amount', css_class='col-12 col-md-4 mb-3'),
                    Column('grand_total_amount', css_class='col-12 col-md-4 mb-3'),
                ),
                Row(
                    Column('status', css_class='col-12 col-md-6 mb-3'),
                ),
                css_class='bg-white p-4 rounded-3 border shadow-sm mb-4'
            )
        )

    def clean_quotation_no(self):
        code = self.cleaned_data.get('quotation_no')
        if not code:
            code = Quotation.generate_quotation_no(existing_pk=self.instance.pk)
        return code

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        transport_cost = cleaned_data.get('estimated_transport_cost') or Decimal('0.00')
        discount_pct = cleaned_data.get('discount_percentage') or Decimal('0.00')
        subtotal = cleaned_data.get('subtotal_amount')
        tax_amount = cleaned_data.get('total_tax_amount')

        from .services import calculate_quotation_totals
        totals = calculate_quotation_totals(
            start_date=start_date,
            end_date=end_date,
            estimated_transport_cost=transport_cost,
            discount_percentage=discount_pct,
            subtotal_amount=subtotal,
            total_tax_amount=tax_amount,
        )

        cleaned_data['subtotal_amount'] = totals['subtotal_amount']
        cleaned_data['total_tax_amount'] = totals['total_tax_amount']
        cleaned_data['grand_total_amount'] = totals['grand_total_amount']

        return cleaned_data


class QuotationItemForm(forms.ModelForm):
    """
    Form for individual machinery line items within a Quotation.
    """
    subtotal_amount = forms.DecimalField(
        label=_("Line Subtotal (LKR)"),
        required=False,
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'min': '0',
            'class': 'form-control item-subtotal bg-light font-monospace fw-semibold',
            'placeholder': '0.00',
        }),
    )

    class Meta:
        model = QuotationItem
        fields = [
            'equipment',
            'start_date',
            'end_date',
            'rate_type',
            'rate_applied',
            'subtotal_amount',
        ]
        widgets = {
            'equipment': forms.Select(attrs={'class': 'form-select item-equipment'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control item-start-date'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control item-end-date'}),
            'rate_type': forms.Select(attrs={'class': 'form-select item-rate-type'}),
            'rate_applied': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'form-control item-rate', 'placeholder': '0.00'}),
        }

    def has_changed(self):
        """
        Prevents extra unselected forms from triggering validation errors.
        An item is considered changed only if equipment is selected or an existing item is modified.
        """
        if not self.instance.pk:
            if not self.data:
                return super().has_changed()
            prefix = self.prefix
            equipment_val = self.data.get(f'{prefix}-equipment')
            if not equipment_val:
                return False
        return super().has_changed()

    def clean(self):
        cleaned_data = super().clean()
        equipment = cleaned_data.get('equipment')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        rate_applied = cleaned_data.get('rate_applied') or Decimal('0.00')

        if equipment:
            days = 1
            if start_date and end_date and end_date >= start_date:
                days = max(1, (end_date - start_date).days + 1)
            calculated_subtotal = (Decimal(days) * Decimal(str(rate_applied))).quantize(Decimal('0.01'))
            if not cleaned_data.get('subtotal_amount') or cleaned_data.get('subtotal_amount') == Decimal('0.00'):
                cleaned_data['subtotal_amount'] = calculated_subtotal
        return cleaned_data


class BaseQuotationItemFormSet(forms.BaseInlineFormSet):
    """
    Custom inline formset for QuotationItems guaranteeing at least one valid line item
    and preventing injection of mandatory blank rows on existing quotations.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing an existing quotation, do not append extra blank forms
        if self.instance and self.instance.pk:
            self.extra = 0

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        valid_items_count = 0
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or self._should_delete_form(form):
                continue
            if form.cleaned_data.get('equipment'):
                valid_items_count += 1

        if valid_items_count == 0:
            raise forms.ValidationError(_("At least one equipment asset line item must be specified for the quotation."))


QuotationItemFormSet = inlineformset_factory(
    Quotation,
    QuotationItem,
    form=QuotationItemForm,
    formset=BaseQuotationItemFormSet,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=False,
)


class RentalContractForm(forms.ModelForm):
    """
    Form for managing binding rental contracts and attaching signed documents.
    """

    class Meta:
        model = RentalContract
        fields = [
            'contract_no',
            'quotation',
            'customer',
            'project_site',
            'equipment',
            'contract_start_date',
            'contract_end_date',
            'billing_cycle',
            'agreed_rate',
            'deposit_paid',
            'status',
            'signed_contract_pdf',
        ]
        widgets = {
            'contract_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'contract_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                HTML('<h5 class="fw-bold mb-3 text-dark"><i class="bi bi-shield-check me-2 text-primary"></i> Contract Agreement Details</h5>'),
                Row(
                    Column('contract_no', css_class='col-12 col-md-4 mb-3'),
                    Column('quotation', css_class='col-12 col-md-4 mb-3'),
                    Column('customer', css_class='col-12 col-md-4 mb-3'),
                ),
                Row(
                    Column('project_site', css_class='col-12 col-md-6 mb-3'),
                    Column('equipment', css_class='col-12 col-md-6 mb-3'),
                ),
                Row(
                    Column('contract_start_date', css_class='col-12 col-md-3 mb-3'),
                    Column('contract_end_date', css_class='col-12 col-md-3 mb-3'),
                    Column('billing_cycle', css_class='col-12 col-md-3 mb-3'),
                    Column('status', css_class='col-12 col-md-3 mb-3'),
                ),
                Row(
                    Column('agreed_rate', css_class='col-12 col-md-4 mb-3'),
                    Column('deposit_paid', css_class='col-12 col-md-4 mb-3'),
                    Column('signed_contract_pdf', css_class='col-12 col-md-4 mb-3'),
                ),
                css_class='bg-white p-4 rounded-3 border shadow-sm mb-4'
            )
        )


class DispatchForm(forms.ModelForm):
    """
    Form for yard officers certifying machinery departure with hour meter, fuel, and checklist.
    """

    class Meta:
        model = DispatchReturn
        fields = [
            'transaction_id',
            'contract',
            'equipment',
            'dispatch_datetime',
            'dispatch_hour_meter',
            'dispatch_fuel_level',
            'dispatch_checklist',
        ]
        widgets = {
            'dispatch_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'dispatch_hour_meter': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'dispatch_fuel_level': forms.NumberInput(attrs={'step': '1', 'min': '0', 'max': '100', 'placeholder': 'Percentage 0-100%'}),
            'dispatch_checklist': forms.Textarea(attrs={'rows': 3, 'placeholder': '{"tires": "pass", "hydraulics": "pass", "engine": "pass", "cabin": "clean"}'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                HTML('<h5 class="fw-bold mb-3 text-dark"><i class="bi bi-box-arrow-up-right me-2 text-primary"></i> Machine Dispatch Handover</h5>'),
                Row(
                    Column('transaction_id', css_class='col-12 col-md-4 mb-3'),
                    Column('contract', css_class='col-12 col-md-4 mb-3'),
                    Column('equipment', css_class='col-12 col-md-4 mb-3'),
                ),
                Row(
                    Column('dispatch_datetime', css_class='col-12 col-md-4 mb-3'),
                    Column('dispatch_hour_meter', css_class='col-12 col-md-4 mb-3'),
                    Column('dispatch_fuel_level', css_class='col-12 col-md-4 mb-3'),
                ),
                Row(
                    Column('dispatch_checklist', css_class='col-12 mb-3'),
                ),
                css_class='bg-white p-4 rounded-3 border shadow-sm mb-4'
            )
        )


class ReturnForm(forms.ModelForm):
    """
    Form for receiving machinery check-in and damage evaluation.
    """

    class Meta:
        model = DispatchReturn
        fields = [
            'return_datetime',
            'return_hour_meter',
            'return_fuel_level',
            'damage_reported',
            'damage_notes',
            'return_checklist',
        ]
        widgets = {
            'return_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'return_hour_meter': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'return_fuel_level': forms.NumberInput(attrs={'step': '1', 'min': '0', 'max': '100'}),
            'damage_notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Detailed description of damages, broken teeth, hydraulic leaks...'}),
            'return_checklist': forms.Textarea(attrs={'rows': 3, 'placeholder': '{"tires": "pass", "hydraulics": "pass", "damage_check": "complete"}'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                HTML('<h5 class="fw-bold mb-3 text-dark"><i class="bi bi-box-arrow-in-down-left me-2 text-success"></i> Equipment Return & Inspection</h5>'),
                Row(
                    Column('return_datetime', css_class='col-12 col-md-4 mb-3'),
                    Column('return_hour_meter', css_class='col-12 col-md-4 mb-3'),
                    Column('return_fuel_level', css_class='col-12 col-md-4 mb-3'),
                ),
                Row(
                    Column('damage_reported', css_class='col-12 mb-3'),
                ),
                Row(
                    Column('damage_notes', css_class='col-12 mb-3'),
                ),
                Row(
                    Column('return_checklist', css_class='col-12 mb-3'),
                ),
                css_class='bg-white p-4 rounded-3 border shadow-sm mb-4'
            )
        )
