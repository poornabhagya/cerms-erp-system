from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class Invoice(TimeStampedModel):
    """
    Invoice Model representing commercial tax invoices, periodic billing cycles,
    and final settlement statements generated upon equipment demobilization/returns.
    Tracks rental subtotal, excess hours, damages, logistics, and statutory taxes.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        UNPAID = 'UNPAID', _('Unpaid')
        PARTIALLY_PAID = 'PARTIALLY_PAID', _('Partially Paid')
        PAID = 'PAID', _('Paid')
        OVERDUE = 'OVERDUE', _('Overdue')
        CANCELLED = 'CANCELLED', _('Cancelled')

    invoice_no = models.CharField(
        _("Invoice Number"),
        max_length=50,
        primary_key=True,
        help_text=_("Unique commercial tax invoice identifier (e.g., INV-2026-0001).")
    )
    contract = models.ForeignKey(
        'rentals.RentalContract',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name=_("Rental Contract"),
        help_text=_("Associated binding rental contract.")
    )
    customer = models.ForeignKey(
        'rentals.Customer',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name=_("Customer Organization"),
        help_text=_("Billed customer organization.")
    )
    invoice_date = models.DateField(
        _("Invoice Issue Date"),
        default=timezone.now,
        help_text=_("Official issuance date of this invoice.")
    )
    due_date = models.DateField(
        _("Payment Due Date"),
        help_text=_("Statutory or contractually agreed payment deadline.")
    )
    billing_period_start = models.DateField(
        _("Billing Period Start"),
        help_text=_("Start date of the operational period covered by this bill.")
    )
    billing_period_end = models.DateField(
        _("Billing Period End"),
        help_text=_("End date of the operational period covered by this bill.")
    )
    rental_subtotal = models.DecimalField(
        _("Base Rental Subtotal (LKR)"),
        max_digits=12,
        decimal_places=2,
        help_text=_("Base machinery rental tariff for the billed duration.")
    )
    excess_hours_charge = models.DecimalField(
        _("Excess Hours Charge (LKR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Supplemental tariff for operating hours exceeding contractual allowance.")
    )
    damage_charges = models.DecimalField(
        _("Damage & Repair Charges (LKR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Assessed maintenance, damage, or cleaning penalties from demobilization inspection.")
    )
    transport_charges = models.DecimalField(
        _("Transport & Logistics Charges (LKR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Mobilization / demobilization low-bed transport charges.")
    )
    tax_amount = models.DecimalField(
        _("Applicable Taxes (VAT/SSCL) (LKR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Statutory Value Added Tax and corporate tax levies.")
    )
    deposit_deducted = models.DecimalField(
        _("Security Deposit Deducted (LKR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Portion of security deposit offset against this invoice.")
    )
    net_total_payable = models.DecimalField(
        _("Net Total Payable (LKR)"),
        max_digits=12,
        decimal_places=2,
        help_text=_("Final settlement amount payable by customer after tax and deposit offset.")
    )
    paid_amount = models.DecimalField(
        _("Paid Amount (LKR)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Cumulative settled amount paid towards this invoice.")
    )
    status = models.CharField(
        _("Invoice Status"),
        max_length=30,
        choices=Status.choices,
        default=Status.UNPAID,
        db_index=True,
        help_text=_("Settlement lifecycle status.")
    )
    invoice_pdf = models.FileField(
        _("Generated Invoice PDF"),
        upload_to='invoices/',
        null=True,
        blank=True,
        help_text=_("Official A4 Tax Invoice document.")
    )

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        ordering = ['-invoice_date', '-created_at']

    def __str__(self):
        return f"{self.invoice_no} - {self.customer.company_name} (LKR {self.net_total_payable:,.2f}) [{self.get_status_display()}]"

    @property
    def balance_due(self) -> Decimal:
        """Calculates outstanding balance remaining to be paid."""
        return max(Decimal('0.00'), self.net_total_payable - self.paid_amount)

    @property
    def is_overdue(self) -> bool:
        """Returns True if invoice has passed due date without full settlement."""
        if self.status in [self.Status.UNPAID, self.Status.PARTIALLY_PAID]:
            return self.due_date < timezone.now().date()
        return self.status == self.Status.OVERDUE

    @property
    def payment_progress_pct(self) -> float:
        """Calculates percentage of net total settled."""
        if self.net_total_payable > Decimal('0.00'):
            return min(100.0, float((self.paid_amount / self.net_total_payable) * 100))
        return 100.0 if self.paid_amount >= self.net_total_payable else 0.0


class Payment(TimeStampedModel):
    """
    Payment Transaction Model tracking incoming settlements, receipts,
    escrow deposit collections, and security deposit refunds.
    """

    class PaymentType(models.TextChoices):
        RENTAL_PAYMENT = 'RENTAL_PAYMENT', _('Rental Invoice Payment')
        SECURITY_DEPOSIT = 'SECURITY_DEPOSIT', _('Security Deposit Receipt')
        DEPOSIT_REFUND = 'DEPOSIT_REFUND', _('Security Deposit Refund')

    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer / Wire')
        CHEQUE = 'CHEQUE', _('Cheque')
        CASH = 'CASH', _('Cash')
        CARD = 'CARD', _('Credit / Debit Card')

    payment_id = models.CharField(
        _("Payment ID"),
        max_length=50,
        primary_key=True,
        help_text=_("Unique payment transaction identifier (e.g., PAY-2026-0001).")
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True,
        verbose_name=_("Settled Invoice"),
        help_text=_("Commercial invoice associated with this payment transaction.")
    )
    customer = models.ForeignKey(
        'rentals.Customer',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name=_("Customer"),
        help_text=_("Customer organization issuing or receiving funds.")
    )
    amount = models.DecimalField(
        _("Transaction Amount (LKR)"),
        max_digits=12,
        decimal_places=2,
        help_text=_("Financial transaction amount in Sri Lankan Rupees.")
    )
    payment_date = models.DateField(
        _("Payment Date"),
        default=timezone.now,
        help_text=_("Date transaction was executed or credited.")
    )
    payment_type = models.CharField(
        _("Payment Type"),
        max_length=30,
        choices=PaymentType.choices,
        default=PaymentType.RENTAL_PAYMENT,
        help_text=_("Commercial purpose of the transaction.")
    )
    payment_method = models.CharField(
        _("Payment Method"),
        max_length=30,
        choices=PaymentMethod.choices,
        help_text=_("Financial channel used for settlement.")
    )
    reference_number = models.CharField(
        _("Reference / Cheque Number"),
        max_length=100,
        blank=True,
        help_text=_("Bank reference number, cheque number, or transaction hash.")
    )
    receipt_pdf = models.FileField(
        _("Payment Receipt PDF"),
        upload_to='receipts/',
        null=True,
        blank=True,
        help_text=_("Official electronic payment receipt.")
    )
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_payments',
        verbose_name=_("Recorded By"),
        help_text=_("Finance/Accounts officer who posted this transaction.")
    )
    notes = models.TextField(
        _("Payment Notes"),
        blank=True,
        help_text=_("Optional accounting annotations or bank details.")
    )

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"{self.payment_id} - {self.customer.company_name} (LKR {self.amount:,.2f}) [{self.get_payment_type_display()}]"


class SecurityDeposit(TimeStampedModel):
    """
    Security Deposit Escrow Model tracking mandatory refundable guarantees,
    offsets against damage/overdue invoices, and return remittances.
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending Receipt')
        HELD = 'HELD', _('Held in Escrow')
        DEDUCTED = 'DEDUCTED', _('Partially / Fully Deducted')
        REFUNDED = 'REFUNDED', _('Fully Refunded')

    deposit_id = models.CharField(
        _("Deposit ID"),
        max_length=50,
        primary_key=True,
        help_text=_("Unique security deposit identifier (e.g., DEP-2026-0001).")
    )
    contract = models.OneToOneField(
        'rentals.RentalContract',
        on_delete=models.PROTECT,
        related_name='security_deposit_record',
        verbose_name=_("Rental Contract"),
        help_text=_("Binding rental contract covered by this security deposit.")
    )
    customer = models.ForeignKey(
        'rentals.Customer',
        on_delete=models.PROTECT,
        related_name='security_deposits',
        verbose_name=_("Customer"),
        help_text=_("Customer organization remitting the deposit.")
    )
    deposit_amount = models.DecimalField(
        _("Total Deposit Required/Agreed (LKR)"),
        max_digits=12,
        decimal_places=2,
        help_text=_("Contractual security deposit escrow amount.")
    )
    received_date = models.DateField(
        _("Received Date"),
        null=True,
        blank=True,
        help_text=_("Date the cash deposit was received into escrow.")
    )
    refunded_amount = models.DecimalField(
        _("Refunded Amount (LKR)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Cumulative deposit amount returned to the customer.")
    )
    deducted_amount = models.DecimalField(
        _("Deducted Amount (LKR)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Cumulative deposit amount retained for damage, excess hours, or invoice settlement.")
    )
    status = models.CharField(
        _("Deposit Status"),
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text=_("Current escrow status of the security deposit.")
    )

    class Meta:
        verbose_name = _("Security Deposit")
        verbose_name_plural = _("Security Deposits")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.deposit_id} - {self.contract.contract_no} (LKR {self.deposit_amount:,.2f}) [{self.get_status_display()}]"

    @property
    def remaining_held_amount(self) -> Decimal:
        """Calculates balance of funds currently held in escrow."""
        return max(Decimal('0.00'), self.deposit_amount - self.deducted_amount - self.refunded_amount)
