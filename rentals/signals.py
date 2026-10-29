"""
Rentals App Signals
Automates business workflows including Return-to-Invoice triggers.
Reference: docs/04_BUSINESS_WORKFLOWS.md
"""

import logging
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DispatchReturn, RentalContract

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DispatchReturn)
def auto_trigger_return_to_invoice(sender, instance, created, **kwargs):
    """
    Automated Return-to-Invoice Trigger:
    When an equipment return is officially recorded (return_datetime is populated)
    and all active on-site equipment under the parent contract has been returned,
    automatically calculate finalized charges (including excess hours and damages)
    and generate the commercial Tax Invoice.
    """
    # Bypass signal if explicitly handled by service layer (which carries damage_charges) or dummy seeding
    if getattr(instance, '_skip_return_invoice_signal', False) or (instance.transaction_id and instance.transaction_id.startswith('TRX-DUMMY-')):
        return

    # Only proceed if return has been officially recorded
    if not instance.return_datetime:
        return

    contract = instance.contract
    if not contract:
        return

    # Check if any active dispatches remain on site for this contract
    has_remaining_active = contract.dispatch_returns.filter(return_datetime__isnull=True).exists()
    if has_remaining_active:
        return

    # Avoid generating duplicate invoices if one already exists
    from finance.models import Invoice
    existing_invoice = contract.invoices.filter(
        status__in=[
            Invoice.Status.UNPAID,
            Invoice.Status.PAID,
            Invoice.Status.PARTIALLY_PAID,
            Invoice.Status.OVERDUE,
        ]
    ).first()

    if existing_invoice:
        if contract.status != RentalContract.Status.CLOSED:
            contract.status = RentalContract.Status.CLOSED
            contract.save(update_fields=['status', 'updated_at'])
        return

    # Automatically trigger final invoice generation via billing engine
    from finance.services import generate_final_rental_invoice
    try:
        invoice = generate_final_rental_invoice(
            contract_id=contract.contract_no,
            user=instance.return_officer,
        )
        if contract.status != RentalContract.Status.CLOSED:
            contract.status = RentalContract.Status.CLOSED
            contract.save(update_fields=['status', 'updated_at'])
        logger.info(
            f"Automated Return-to-Invoice generated invoice '{invoice.invoice_no}' "
            f"for Contract '{contract.contract_no}'."
        )
    except Exception as e:
        logger.error(
            f"Automated Return-to-Invoice signal failed for Contract '{contract.contract_no}': {e}",
            exc_info=True
        )
