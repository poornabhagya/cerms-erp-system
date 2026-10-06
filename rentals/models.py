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


class Quotation(TimeStampedModel):
    """
    Quotation Model representing formal pricing offers, machinery duration estimates,
    transport fees, and multi-tier managerial approval workflows.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PENDING_INTERNAL_APPROVAL = 'PENDING_INTERNAL_APPROVAL', _('Pending Internal Approval')
        APPROVED_BY_MANAGEMENT = 'APPROVED_BY_MANAGEMENT', _('Approved by Management')
        SENT_TO_CUSTOMER = 'SENT_TO_CUSTOMER', _('Sent to Customer')
        ACCEPTED = 'ACCEPTED', _('Accepted by Customer')
        REJECTED = 'REJECTED', _('Rejected')
        EXPIRED = 'EXPIRED', _('Expired')
        CONVERTED = 'CONVERTED', _('Converted to Contract')

    class RateType(models.TextChoices):
        DAILY = 'DAILY', _('Daily')
        WEEKLY = 'WEEKLY', _('Weekly')
        MONTHLY = 'MONTHLY', _('Monthly')

    quotation_no = models.CharField(
        _("Quotation Number"),
        max_length=50,
        primary_key=True,
        help_text=_("Unique identifier (e.g., QT-2026-0001).")
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='quotations',
        verbose_name=_("Customer"),
        help_text=_("Customer organization requesting the machinery quotation.")
    )
    project_site = models.ForeignKey(
        ProjectSite,
        on_delete=models.PROTECT,
        related_name='quotations',
        verbose_name=_("Project Site"),
        help_text=_("Designated construction site for equipment delivery.")
    )
    equipment = models.ForeignKey(
        'fleet.Equipment',
        on_delete=models.PROTECT,
        related_name='quotations',
        verbose_name=_("Equipment Asset"),
        help_text=_("Machinery asset requested for rental.")
    )
    start_date = models.DateField(
        _("Rental Start Date"),
        help_text=_("Commencement date of prospective rental.")
    )
    end_date = models.DateField(
        _("Rental End Date"),
        help_text=_("Estimated completion/return date of rental.")
    )
    rate_applied = models.DecimalField(
        _("Applied Rate (LKR)"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Unit rental rate agreed for this quotation.")
    )
    rate_type = models.CharField(
        _("Rate Type"),
        max_length=20,
        choices=RateType.choices,
        default=RateType.DAILY,
        help_text=_("Rate frequency tier (Daily, Weekly, Monthly).")
    )
    estimated_transport_cost = models.DecimalField(
        _("Estimated Transport Cost (LKR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Estimated mobilization and demobilization transport fee.")
    )
    security_deposit_required = models.DecimalField(
        _("Security Deposit Required (LKR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Refundable cash deposit or escrow required before machine handover.")
    )
    discount_percentage = models.DecimalField(
        _("Discount Percentage (%)"),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Approved commercial discount percentage (0-100%).")
    )
    subtotal_amount = models.DecimalField(
        _("Subtotal Amount (LKR)"),
        max_digits=12,
        decimal_places=2,
        help_text=_("Base rental charge before tax and transport.")
    )
    total_tax_amount = models.DecimalField(
        _("Total Tax Amount (LKR)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Applicable statutory taxes (e.g., VAT, SSCL).")
    )
    grand_total_amount = models.DecimalField(
        _("Grand Total Amount (LKR)"),
        max_digits=12,
        decimal_places=2,
        help_text=_("Total quotation value including rental, transport, and taxes.")
    )
    status = models.CharField(
        _("Quotation Status"),
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text=_("Commercial lifecycle status of this quotation.")
    )
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_quotations',
        verbose_name=_("Approved By"),
        help_text=_("Management user who reviewed and authorized this quotation.")
    )
    approval_date = models.DateTimeField(
        _("Approval Date & Time"),
        null=True,
        blank=True,
        help_text=_("Timestamp when managerial authorization was granted.")
    )

    class Meta:
        verbose_name = _("Quotation")
        verbose_name_plural = _("Quotations")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.quotation_no} - {self.customer.company_name} ({self.get_status_display()})"

    @property
    def duration_days(self) -> int:
        """Calculates total rental calendar days inclusive of start and end dates."""
        if self.start_date and self.end_date:
            return max(1, (self.end_date - self.start_date).days + 1)
        return 1

    @property
    def rental_duration_days(self) -> int:
        """Alias for duration_days for template compatibility."""
        return self.duration_days

    @property
    def discount_amount(self) -> Decimal:
        """Calculates commercial discount amount in LKR."""
        base = self.subtotal_amount if self.subtotal_amount is not None else (Decimal(self.duration_days) * (self.rate_applied or Decimal('0.00')))
        return ((base * (self.discount_percentage or Decimal('0.00'))) / Decimal('100.00')).quantize(Decimal('0.01'))

    def calculate_totals(self) -> dict:
        """
        Calculates quote figures:
        - Base Tariff (subtotal_amount)
        - Discount Amount
        - Transport
        - VAT (total_tax_amount)
        - Grand Total: (Base Tariff + Transport + VAT) - Discount
        """
        days = Decimal(self.duration_days)
        rate = self.rate_applied or Decimal('0.00')
        transport = self.estimated_transport_cost or Decimal('0.00')
        discount_pct = self.discount_percentage or Decimal('0.00')

        base_tariff = self.subtotal_amount if self.subtotal_amount is not None else (days * rate)
        discount_amt = (base_tariff * discount_pct) / Decimal('100.00')

        if self.total_tax_amount is not None and self.total_tax_amount > Decimal('0.00'):
            tax_amt = self.total_tax_amount
        else:
            taxable = max(Decimal('0.00'), (base_tariff - discount_amt) + transport)
            tax_amt = (taxable * Decimal('0.18')).quantize(Decimal('0.01'))

        # Formula: (Base Tariff + Transport + VAT) - Discount
        grand_total = (base_tariff + transport + tax_amt) - discount_amt

        return {
            'duration_days': self.duration_days,
            'base_tariff': base_tariff.quantize(Decimal('0.01')),
            'discount_amount': discount_amt.quantize(Decimal('0.01')),
            'transport_cost': transport.quantize(Decimal('0.01')),
            'tax_amount': tax_amt.quantize(Decimal('0.01')),
            'grand_total_amount': grand_total.quantize(Decimal('0.01')),
        }

    def save(self, *args, **kwargs):
        """Ensure financial totals adhere strictly to business calculation formulas."""
        if self.subtotal_amount is None and self.rate_applied is not None:
            self.subtotal_amount = Decimal(self.duration_days) * self.rate_applied

        base_tariff = self.subtotal_amount or (Decimal(self.duration_days) * (self.rate_applied or Decimal('0.00')))
        discount_amt = (base_tariff * (self.discount_percentage or Decimal('0.00'))) / Decimal('100.00')
        transport = self.estimated_transport_cost or Decimal('0.00')

        if self.total_tax_amount is None:
            taxable = max(Decimal('0.00'), (base_tariff - discount_amt) + transport)
            self.total_tax_amount = (taxable * Decimal('0.18')).quantize(Decimal('0.01'))

        vat = self.total_tax_amount or Decimal('0.00')

        # Auto-correct grand total if empty or if previously set to just the discount amount
        if self.grand_total_amount is None or self.grand_total_amount == discount_amt:
            self.grand_total_amount = ((base_tariff + transport + vat) - discount_amt).quantize(Decimal('0.01'))

        super().save(*args, **kwargs)

    @property
    def is_approved(self) -> bool:
        """Returns True if the quotation has passed managerial approval."""
        return self.status in [
            self.Status.APPROVED_BY_MANAGEMENT,
            self.Status.SENT_TO_CUSTOMER,
            self.Status.ACCEPTED,
            self.Status.CONVERTED,
        ]


class RentalContract(TimeStampedModel):
    """
    Rental Contract Model representing binding legal agreements executing equipment rentals.
    Tracks billing cycles, escrow deposit payments, signed documents, and dispatch status.
    """

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        DISPATCHED = 'DISPATCHED', _('Dispatched / In Transit')
        ON_RENT = 'ON_RENT', _('On Rent')
        PENDING_RETURN = 'PENDING_RETURN', _('Pending Return')
        RETURNED = 'RETURNED', _('Returned')
        CLOSED = 'CLOSED', _('Closed & Invoiced')
        TERMINATED = 'TERMINATED', _('Terminated Early')

    class BillingCycle(models.TextChoices):
        WEEKLY = 'WEEKLY', _('Weekly')
        MONTHLY = 'MONTHLY', _('Monthly')
        ON_RETURN = 'ON_RETURN', _('On Return')

    contract_no = models.CharField(
        _("Contract Number"),
        max_length=50,
        primary_key=True,
        help_text=_("Unique legal contract identifier (e.g., CNT-2026-0001).")
    )
    quotation = models.OneToOneField(
        Quotation,
        on_delete=models.PROTECT,
        related_name='contract',
        verbose_name=_("Originating Quotation"),
        help_text=_("Accepted commercial quotation converted into this binding contract.")
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='contracts',
        verbose_name=_("Customer"),
        help_text=_("Contracting customer organization.")
    )
    project_site = models.ForeignKey(
        ProjectSite,
        on_delete=models.PROTECT,
        related_name='contracts',
        verbose_name=_("Project Site"),
        help_text=_("Designated construction site location for machine deployment.")
    )
    equipment = models.ForeignKey(
        'fleet.Equipment',
        on_delete=models.PROTECT,
        related_name='contracts',
        verbose_name=_("Equipment Asset"),
        help_text=_("Machinery asset contracted for rental.")
    )
    contract_start_date = models.DateField(
        _("Contract Start Date"),
        help_text=_("Official start date of the rental period.")
    )
    contract_end_date = models.DateField(
        _("Contract End Date"),
        help_text=_("Agreed contractual completion / return date.")
    )
    billing_cycle = models.CharField(
        _("Billing Cycle"),
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
        help_text=_("Periodic invoice schedule (Weekly, Monthly, On Return).")
    )
    agreed_rate = models.DecimalField(
        _("Agreed Rate (LKR)"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Final agreed rental rate per period.")
    )
    deposit_paid = models.DecimalField(
        _("Deposit Paid (LKR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Actual security deposit amount collected and held in escrow.")
    )
    status = models.CharField(
        _("Contract Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text=_("Operational and billing state of the rental contract.")
    )
    signed_contract_pdf = models.FileField(
        _("Signed Contract PDF"),
        upload_to='contracts/signed_pdfs/',
        null=True,
        blank=True,
        help_text=_("Scanned or digital copy of the countersigned rental contract.")
    )

    class Meta:
        verbose_name = _("Rental Contract")
        verbose_name_plural = _("Rental Contracts")
        ordering = ['-contract_start_date', '-created_at']

    def __str__(self):
        return f"{self.contract_no} - {self.customer.company_name} ({self.equipment.asset_code})"


class DispatchReturn(TimeStampedModel):
    """
    Dispatch and Return Logistics Inspection Log Model.
    Captures exact machine telemetry (hour meter, fuel level), handover checklist,
    and returns inspection for excess hour and damage settlement.
    """

    transaction_id = models.CharField(
        _("Transaction ID"),
        max_length=50,
        primary_key=True,
        help_text=_("Unique logistics transaction identifier (e.g., TRX-2026-0001).")
    )
    contract = models.ForeignKey(
        RentalContract,
        on_delete=models.PROTECT,
        related_name='dispatch_returns',
        verbose_name=_("Rental Contract"),
        help_text=_("Contract governing this machine handover.")
    )
    equipment = models.ForeignKey(
        'fleet.Equipment',
        on_delete=models.PROTECT,
        related_name='dispatch_returns',
        verbose_name=_("Equipment Asset"),
        help_text=_("Equipment asset being dispatched or returned.")
    )

    # --- Dispatch Phase (Mobilization) ---
    dispatch_datetime = models.DateTimeField(
        _("Dispatch Date & Time"),
        help_text=_("Exact date and time machinery exited depot for mobilization.")
    )
    dispatch_hour_meter = models.DecimalField(
        _("Dispatch Hour Meter (hrs)"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Operating cumulative hour meter at time of mobilization.")
    )
    dispatch_fuel_level = models.DecimalField(
        _("Dispatch Fuel Level (%)"),
        max_digits=5,
        decimal_places=2,
        help_text=_("Opening fuel tank level (Percentage 0-100%).")
    )
    dispatch_officer = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='dispatched_logs',
        verbose_name=_("Dispatch Officer"),
        help_text=_("Operations or Yard officer certifying machine departure.")
    )
    dispatch_checklist = models.JSONField(
        _("Dispatch Inspection Checklist"),
        default=dict,
        blank=True,
        help_text=_("Structured pre-delivery condition checklist (Tires, Hydraulic, Engine, Cabin).")
    )

    # --- Return Phase (Demobilization & Inspection) ---
    return_datetime = models.DateTimeField(
        _("Return Date & Time"),
        null=True,
        blank=True,
        help_text=_("Date and time machinery was received back at the depot.")
    )
    return_hour_meter = models.DecimalField(
        _("Return Hour Meter (hrs)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Closing cumulative hour meter upon check-in.")
    )
    return_fuel_level = models.DecimalField(
        _("Return Fuel Level (%)"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Closing fuel tank level upon return.")
    )
    return_officer = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='received_logs',
        verbose_name=_("Return Receiving Officer"),
        help_text=_("Workshop or receiving officer conducting check-in inspection.")
    )
    return_checklist = models.JSONField(
        _("Return Inspection Checklist"),
        default=dict,
        blank=True,
        help_text=_("Structured return condition checklist.")
    )
    damage_reported = models.BooleanField(
        _("Damage / Defects Reported"),
        default=False,
        help_text=_("Flag indicating whether physical damage or breakdown occurred on-site.")
    )
    damage_notes = models.TextField(
        _("Damage Description & Assessment Notes"),
        blank=True,
        help_text=_("Detailed notes on identified damages, component replacements, or repair estimates.")
    )
    excess_hours_calculated = models.DecimalField(
        _("Calculated Excess Operating Hours (hrs)"),
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Billable operating hours exceeding the contractual standard allowance.")
    )

    class Meta:
        verbose_name = _("Dispatch & Return Log")
        verbose_name_plural = _("Dispatch & Return Logs")
        ordering = ['-dispatch_datetime']

    def __str__(self):
        return f"{self.transaction_id} - {self.equipment.asset_code} ({self.contract.contract_no})"

    @property
    def hours_operated(self) -> Decimal:
        """Calculates total hours operated during this rental period."""
        if self.return_hour_meter is not None and self.dispatch_hour_meter is not None:
            return max(Decimal('0.00'), self.return_hour_meter - self.dispatch_hour_meter)
        return Decimal('0.00')
