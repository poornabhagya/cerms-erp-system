from decimal import Decimal
from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Div, HTML, Submit

from .models import Invoice, Payment, SecurityDeposit
from rentals.models import RentalContract, Customer


class InvoiceGenerationForm(forms.Form):
    """
    Form for configuring settlement parameters when generating a final rental invoice.
    """
    contract = forms.ModelChoiceField(
        queryset=RentalContract.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        label="Rental Contract"
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Payment Due Date"
    )
    excess_hours_rate = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'form-control'}),
        label="Hourly Excess Rate (LKR)",
        help_text="Leave blank to use contract's derived standard hourly tariff."
    )
    damage_charges = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=Decimal('0.00'),
        required=False,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'form-control'}),
        label="Damage / Cleaning Charges (LKR)",
        help_text="Assessed penalties from demobilization inspection checklist."
    )
    apply_security_deposit = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        label="Automatically Offset Held Security Deposit",
        help_text="Deducts held escrow cash deposit from final net payable amount."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('due_date'):
            self.initial['due_date'] = timezone.now().date() + timezone.timedelta(days=30)
        self.helper = FormHelper()
        self.helper.form_tag = False


class PaymentForm(forms.ModelForm):
    """
    Form for posting settlement payments and escrow deposit transactions.
    """

    class Meta:
        model = Payment
        fields = [
            'customer',
            'invoice',
            'amount',
            'payment_date',
            'payment_type',
            'payment_method',
            'reference_number',
            'receipt_pdf',
            'notes',
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'invoice': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'class': 'form-control', 'id': 'id_payment_amount'}),
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. TXN-HNB-987654 / CHQ-100234'}),
            'receipt_pdf': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Bank details, remitter details, or accounting annotations...'}),
        }

    def __init__(self, *args, **kwargs):
        self.invoice_instance = kwargs.pop('invoice', None)
        super().__init__(*args, **kwargs)

        if self.invoice_instance:
            self.fields['invoice'].initial = self.invoice_instance
            self.fields['invoice'].required = False
            self.fields['customer'].initial = self.invoice_instance.customer
            self.fields['customer'].required = False
            self.fields['amount'].initial = self.invoice_instance.balance_due

        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean(self):
        cleaned_data = super().clean()
        if self.invoice_instance:
            cleaned_data['invoice'] = self.invoice_instance
            cleaned_data['customer'] = self.invoice_instance.customer
        elif cleaned_data.get('invoice') and not cleaned_data.get('customer'):
            cleaned_data['customer'] = cleaned_data['invoice'].customer

        return cleaned_data


class SecurityDepositRefundForm(forms.Form):
    """
    Form for processing full or partial escrow refunds upon contract closure.
    """
    refund_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'class': 'form-control'}),
        label="Refund Amount (LKR)"
    )
    payment_method = forms.ChoiceField(
        choices=Payment.PaymentMethod.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Disbursement Method"
    )
    reference_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cheque / Wire Transfer Reference'}),
        label="Bank Reference / Cheque No."
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Refund authorization notes...'}),
        label="Accounting Notes"
    )

    def __init__(self, deposit=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deposit = deposit
        if deposit:
            self.fields['refund_amount'].initial = deposit.remaining_held_amount
            self.fields['refund_amount'].widget.attrs['max'] = str(deposit.remaining_held_amount)
