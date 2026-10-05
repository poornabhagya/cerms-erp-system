from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field

from .models import Customer, ProjectSite


class CustomerForm(forms.ModelForm):
    """Form for registering and updating Customer / Corporate Client records."""

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
            'status',
        ]
        widgets = {
            'billing_address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Full corporate billing address...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
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
                    Column('vat_tax_number', css_class='col-12 col-md-6 mb-3'),
                    Column('credit_limit', css_class='col-12 col-md-3 mb-3'),
                    Column('status', css_class='col-12 col-md-3 mb-3'),
                ),
                Row(
                    Column('billing_address', css_class='col-12 mb-3'),
                ),
                css_class='bg-white p-4 rounded-3 border mb-4'
            )
        )


class ProjectSiteForm(forms.ModelForm):
    """Form for registering and modifying Project Construction Site destinations."""

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
            'site_address': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Exact physical delivery location...'}),
            'gps_coordinates': forms.TextInput(attrs={'placeholder': 'e.g. 6.9271,79.8612'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
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
                Row(
                    Column('site_contact_person', css_class='col-12 col-md-6 mb-3'),
                    Column('site_contact_phone', css_class='col-12 col-md-6 mb-3'),
                ),
                css_class='bg-white p-4 rounded-3 border mb-4'
            )
        )
