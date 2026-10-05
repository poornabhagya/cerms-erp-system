from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class Customer(TimeStampedModel):
    """
    Customer / Client organization master record.
    Tracks corporate credentials, contact telemetry, tax registrations, and credit limits.
    """

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        BLOCKED = 'BLOCKED', _('Blocked / Credit Hold')
        INACTIVE = 'INACTIVE', _('Inactive')

    customer_code = models.CharField(
        _("Customer Code"),
        max_length=50,
        primary_key=True,
        help_text=_("Unique identifier (e.g., CUST-2026-001).")
    )
    company_name = models.CharField(
        _("Company / Corporate Name"),
        max_length=200,
        help_text=_("Registered corporate enterprise or contractor name.")
    )
    contact_person = models.CharField(
        _("Primary Contact Person"),
        max_length=150,
        help_text=_("Full name of primary commercial representative or site manager.")
    )
    phone = models.CharField(
        _("Contact Phone"),
        max_length=20,
        help_text=_("Primary corporate or direct mobile number.")
    )
    email = models.EmailField(
        _("Billing Email"),
        help_text=_("Official email for sending quotations, contracts, and invoices.")
    )
    billing_address = models.TextField(
        _("Billing Address"),
        help_text=_("Official registered corporate billing address.")
    )
    vat_tax_number = models.CharField(
        _("VAT / Tax Identification No."),
        max_length=50,
        blank=True,
        help_text=_("Government tax registration or VAT number (if registered).")
    )
    credit_limit = models.DecimalField(
        _("Credit Limit (LKR)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Maximum approved outstanding receivables credit limit in LKR.")
    )
    current_outstanding_balance = models.DecimalField(
        _("Outstanding Balance (LKR)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Current cumulative unpaid receivables balance.")
    )
    status = models.CharField(
        _("Account Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text=_("Commercial account standing.")
    )

    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")
        ordering = ['company_name']

    def __str__(self):
        return f"{self.customer_code} - {self.company_name}"

    @property
    def available_credit(self) -> Decimal:
        """Returns remaining credit headroom before hitting credit limit."""
        return max(Decimal('0.00'), self.credit_limit - self.current_outstanding_balance)

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class ProjectSite(TimeStampedModel):
    """
    Project Site / Construction Location associated with a customer.
    Tracks site location, delivery destination, GPS coordinates, and on-site contacts.
    """

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active Site')
        COMPLETED = 'COMPLETED', _('Completed / Handed Over')

    project_code = models.CharField(
        _("Project Code"),
        max_length=50,
        primary_key=True,
        help_text=_("Unique identifier (e.g., PRJ-COL-001).")
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='project_sites',
        verbose_name=_("Customer"),
        help_text=_("Customer company operating this construction project.")
    )
    project_name = models.CharField(
        _("Project Name"),
        max_length=200,
        help_text=_("Name of the construction or engineering site.")
    )
    site_address = models.TextField(
        _("Site Physical Address"),
        help_text=_("Physical delivery destination address for equipment mobilization.")
    )
    gps_coordinates = models.CharField(
        _("GPS Coordinates (Lat, Long)"),
        max_length=100,
        blank=True,
        help_text=_("Geographic coordinates (e.g., 6.9271,79.8612) for logistics navigation.")
    )
    site_contact_person = models.CharField(
        _("On-Site Contact Person"),
        max_length=150,
        blank=True,
        help_text=_("Resident engineer or site supervisor receiving machinery.")
    )
    site_contact_phone = models.CharField(
        _("On-Site Contact Phone"),
        max_length=20,
        blank=True,
        help_text=_("Direct phone number of on-site contact person.")
    )
    status = models.CharField(
        _("Site Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text=_("Operational status of the construction project.")
    )

    class Meta:
        verbose_name = _("Project Site")
        verbose_name_plural = _("Project Sites")
        ordering = ['project_name']

    def __str__(self):
        return f"{self.project_code} - {self.project_name} ({self.customer.company_name})"
