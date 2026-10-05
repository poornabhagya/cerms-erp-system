from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class Customer(TimeStampedModel):
    """
    Customer Master Model representing B2B corporate clients, construction contractors,
    and individual clients renting heavy machinery and equipment assets.
    """

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        BLOCKED = 'BLOCKED', _('Blocked')
        INACTIVE = 'INACTIVE', _('Inactive')

    customer_code = models.CharField(
        _("Customer Code"),
        max_length=50,
        primary_key=True,
        help_text=_("Unique customer identifier (e.g., CUST-2026-001).")
    )
    company_name = models.CharField(
        _("Company / Entity Name"),
        max_length=200,
        help_text=_("Registered legal business name or individual client name.")
    )
    contact_person = models.CharField(
        _("Primary Contact Person"),
        max_length=150,
        help_text=_("Designated point of contact representative.")
    )
    phone = models.CharField(
        _("Primary Phone Number"),
        max_length=20,
        help_text=_("Primary telephone or mobile number.")
    )
    email = models.EmailField(
        _("Billing & Notification Email"),
        help_text=_("Email address for quotations, contracts, invoices, and payment receipts.")
    )
    billing_address = models.TextField(
        _("Billing Address"),
        help_text=_("Official registered corporate or residential billing address.")
    )
    vat_tax_number = models.CharField(
        _("VAT / Tax Identification Number"),
        max_length=50,
        blank=True,
        help_text=_("Government registered tax identification number (if applicable).")
    )
    credit_limit = models.DecimalField(
        _("Credit Limit (LKR)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Approved maximum outstanding credit ceiling before requiring managerial approval.")
    )
    current_outstanding_balance = models.DecimalField(
        _("Current Outstanding Balance (LKR)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Current cumulative unpaid invoice amount across active and completed rentals.")
    )
    status = models.CharField(
        _("Account Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text=_("Operational standing governing quotation and rental eligibility.")
    )

    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")
        ordering = ['company_name']

    def __str__(self):
        return f"{self.customer_code} - {self.company_name} ({self.get_status_display()})"

    @property
    def available_credit(self) -> Decimal:
        """Calculates remaining available credit margin for new quotation commitments."""
        return max(Decimal('0.00'), self.credit_limit - self.current_outstanding_balance)

    @property
    def is_eligible_for_rentals(self) -> bool:
        """Returns True if the customer account is in good standing (Active)."""
        return self.status == self.Status.ACTIVE


class ProjectSite(TimeStampedModel):
    """
    Project Site Model representing physical construction sites, infrastructure projects,
    or geographic locations where rented machinery is deployed, monitored, and returned.
    """

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        COMPLETED = 'COMPLETED', _('Completed')

    project_code = models.CharField(
        _("Project Site Code"),
        max_length=50,
        primary_key=True,
        help_text=_("Unique project identifier (e.g., PRJ-COL-001).")
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='project_sites',
        verbose_name=_("Customer"),
        help_text=_("Customer organization responsible for this project site.")
    )
    project_name = models.CharField(
        _("Project / Site Name"),
        max_length=200,
        help_text=_("Descriptive project name (e.g., Central Expressway Section III).")
    )
    site_address = models.TextField(
        _("Physical Site Address"),
        help_text=_("Full physical site location and delivery dispatch coordinates.")
    )
    gps_coordinates = models.CharField(
        _("GPS Coordinates"),
        max_length=100,
        blank=True,
        help_text=_("Geographic coordinates (e.g., 6.9271,79.8612) for dispatch mapping.")
    )
    site_contact_person = models.CharField(
        _("On-Site Contact Person"),
        max_length=150,
        blank=True,
        help_text=_("On-site engineer, supervisor, or receiving coordinator.")
    )
    site_contact_phone = models.CharField(
        _("On-Site Contact Phone"),
        max_length=20,
        blank=True,
        help_text=_("Direct phone contact for site dispatch and equipment handover.")
    )
    status = models.CharField(
        _("Site Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text=_("Operational status of this construction project site.")
    )

    class Meta:
        verbose_name = _("Project Site")
        verbose_name_plural = _("Project Sites")
        ordering = ['project_name']

    def __str__(self):
        return f"{self.project_code} - {self.project_name} ({self.customer.company_name})"
