from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field

from .models import Customer, ProjectSite


class CustomerForm(forms.ModelForm):
    """
    Form for registering and updating Customer commercial master records with Crispy Bootstrap 5 styling.
    """

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


class ProjectSiteForm(forms.ModelForm):
    """
    Form for registering and updating physical Project Sites linked to Customer organizations.
    """

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
