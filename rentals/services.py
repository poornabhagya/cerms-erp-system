import uuid
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from typing import Dict, Any, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from fleet.models import Equipment
from .models import Customer, Quotation, QuotationItem, RentalContract, RentalContractItem, DispatchReturn


def calculate_quotation_totals(
    items=None,
    start_date=None,
    end_date=None,
    rate_applied: Decimal = Decimal('0.00'),
    rate_type: str = 'DAILY',
    estimated_transport_cost: Decimal = Decimal('0.00'),
    discount_percentage: Decimal = Decimal('0.00'),
    subtotal_amount: Optional[Decimal] = None,
    total_tax_amount: Optional[Decimal] = None,
    tax_rate: Decimal = Decimal('0.18'),
) -> Dict[str, Decimal]:
    """
    Computes commercial quotation financial figures adhering strictly to the business rule:
    Taxable Base = (Base Tariff - Discount Amount) + Estimated Transport Cost
    VAT (18%) = Taxable Base * 0.18
    Grand Total = Taxable Base + VAT = (Base Tariff + Transport + VAT) - Discount

    Parameters:
    - items: Optional list/iterable of QuotationItem objects or item dicts with 'subtotal_amount'
    - start_date / end_date: Rental schedule to calculate duration in days
    - rate_applied: Rate per unit (for single-item fallback)
    - estimated_transport_cost: Round-trip logistics
    - discount_percentage: Percentage discount (0-100%)
    - subtotal_amount: Base tariff if pre-set, otherwise computed from items or duration_days * rate_applied
    - total_tax_amount: Custom VAT/tax if pre-set, otherwise statutory 18% on Taxable Base
    """
    days = 1
    if start_date and end_date:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        if end_date >= start_date:
            days = max(1, (end_date - start_date).days + 1)

    transport = Decimal(str(estimated_transport_cost or 0))
    discount_pct = Decimal(str(discount_percentage or 0))

    if items:
        # Sum subtotals of all line items
        base_tariff = Decimal('0.00')
        for itm in items:
            if isinstance(itm, dict):
                sub = itm.get('subtotal_amount')
                if sub is not None:
                    base_tariff += Decimal(str(sub))
                else:
                    itm_rate = Decimal(str(itm.get('rate_applied') or 0))
                    itm_s = itm.get('start_date') or start_date
                    itm_e = itm.get('end_date') or end_date
                    itm_days = days
                    if itm_s and itm_e:
                        if isinstance(itm_s, str):
                            itm_s = datetime.strptime(itm_s, '%Y-%m-%d').date()
                        if isinstance(itm_e, str):
                            itm_e = datetime.strptime(itm_e, '%Y-%m-%d').date()
                        if itm_e >= itm_s:
                            itm_days = max(1, (itm_e - itm_s).days + 1)
                    base_tariff += (Decimal(itm_days) * itm_rate).quantize(Decimal('0.01'))
            elif hasattr(itm, 'subtotal_amount'):
                base_tariff += Decimal(str(itm.subtotal_amount or 0))
    elif subtotal_amount is not None:
        base_tariff = Decimal(str(subtotal_amount))
    else:
        rate = Decimal(str(rate_applied or 0))
        base_tariff = Decimal(days) * rate

    discount_amount = ((base_tariff * discount_pct) / Decimal('100.00')).quantize(Decimal('0.01'))
    taxable_base = max(Decimal('0.00'), (base_tariff - discount_amount) + transport)

    if total_tax_amount is not None and Decimal(str(total_tax_amount)) > Decimal('0.00'):
        tax_amount = Decimal(str(total_tax_amount)).quantize(Decimal('0.01'))
    else:
        tax_amount = (taxable_base * Decimal(str(tax_rate))).quantize(Decimal('0.01'))

    # Formula: Grand Total = Taxable Base + VAT = (Base Tariff + Transport + VAT) - Discount
    grand_total = (taxable_base + tax_amount).quantize(Decimal('0.01'))

    return {
        'duration_days': days,
        'base_tariff': base_tariff.quantize(Decimal('0.01')),
        'subtotal_amount': base_tariff.quantize(Decimal('0.01')),
        'discount_amount': discount_amount.quantize(Decimal('0.01')),
        'taxable_base': taxable_base.quantize(Decimal('0.01')),
        'estimated_transport_cost': transport.quantize(Decimal('0.01')),
        'total_tax_amount': tax_amount.quantize(Decimal('0.01')),
        'grand_total_amount': grand_total.quantize(Decimal('0.01')),
    }


def validate_customer_credit_limit(customer: Customer, new_quotation_amount: Decimal, raise_exception: bool = False) -> Dict[str, Any]:
    """
    Evaluates customer creditworthiness, operational standing, and outstanding balance against
    their approved credit ceiling.
    """
    amount = Decimal(str(new_quotation_amount or 0))
    current_balance = Decimal(str(customer.current_outstanding_balance or 0))
    credit_limit = Decimal(str(customer.credit_limit or 0))
    projected_exposure = current_balance + amount
    available_credit = max(Decimal('0.00'), credit_limit - current_balance) if credit_limit > Decimal('0.00') else Decimal('0.00')
    remaining_margin = max(Decimal('0.00'), credit_limit - projected_exposure) if credit_limit > Decimal('0.00') else Decimal('0.00')

    # 1. Customer Account Standing Check
    if not customer.is_eligible_for_rentals:
        error_msg = _(
            f"Customer '{customer.company_name}' ({customer.customer_code}) is currently in '{customer.get_status_display()}' status. "
            f"New rentals and quotations cannot be processed."
        )
        if raise_exception:
            raise ValidationError(error_msg)
        return {
            'is_approved': False,
            'allowed': False,
            'requires_management_override': True,
            'customer_code': customer.customer_code,
            'customer_status': customer.status,
            'credit_limit': credit_limit,
            'current_outstanding_balance': current_balance,
            'new_quotation_amount': amount,
            'projected_total_exposure': projected_exposure,
            'available_credit': available_credit,
            'remaining_available_margin': Decimal('0.00'),
            'margin_remaining': Decimal('0.00'),
            'excess_amount': max(Decimal('0.00'), projected_exposure - credit_limit),
            'message': str(error_msg)
        }

    # 2. Credit Ceiling Assessment
    if credit_limit > Decimal('0.00') and projected_exposure > credit_limit:
        excess = projected_exposure - credit_limit
        warning_msg = _(
            f"Credit limit exceeded for '{customer.company_name}'. "
            f"Approved Limit: LKR {credit_limit:,.2f} | Current Balance: LKR {current_balance:,.2f} | "
            f"New Amount: LKR {amount:,.2f} | Projected Exposure: LKR {projected_exposure:,.2f} | "
            f"Excess: LKR {excess:,.2f}. Requires Managerial Approval."
        )
        if raise_exception:
            raise ValidationError(warning_msg)
        return {
            'is_approved': False,
            'allowed': False,
            'requires_management_override': True,
            'customer_code': customer.customer_code,
            'customer_status': customer.status,
            'credit_limit': credit_limit,
            'current_outstanding_balance': current_balance,
            'new_quotation_amount': amount,
            'projected_total_exposure': projected_exposure,
            'available_credit': available_credit,
            'remaining_available_margin': Decimal('0.00'),
            'margin_remaining': Decimal('0.00'),
            'excess_amount': excess,
            'message': str(warning_msg)
        }

    # 3. Credit Approved
    success_msg = _(
        f"Credit validation passed for '{customer.company_name}'. "
        f"Projected exposure (LKR {projected_exposure:,.2f}) is within approved credit limits."
    )
    return {
        'is_approved': True,
        'allowed': True,
        'requires_management_override': False,
        'customer_code': customer.customer_code,
        'customer_status': customer.status,
        'credit_limit': credit_limit,
        'current_outstanding_balance': current_balance,
        'new_quotation_amount': amount,
        'projected_total_exposure': projected_exposure,
        'available_credit': available_credit,
        'remaining_available_margin': remaining_margin,
        'margin_remaining': remaining_margin,
        'excess_amount': Decimal('0.00'),
        'message': str(success_msg)
    }


def convert_quotation_to_contract(quotation_id: str, user=None, billing_cycle: str = 'MONTHLY') -> RentalContract:
    """
    Converts an accepted commercial quotation into a legally binding RentalContract.
    Generates corresponding RentalContractItem line entries for all quoted assets,
    transitions each machinery asset to RESERVED, and audits status changes.

    Step 4.2 State Machine Workflow:
    1. Validates quotation status is ACCEPTED (or approved).
    2. Creates RentalContract with agreed financial values.
    3. Creates RentalContractItem records for each quoted equipment asset.
    4. Transitions each Equipment.status -> RESERVED.
    5. Marks Quotation.status -> CONVERTED.
    """
    with transaction.atomic():
        quotation = Quotation.objects.select_for_update().get(quotation_no=quotation_id)

        if hasattr(quotation, 'contract'):
            raise ValidationError(f"Quotation '{quotation.quotation_no}' has already been converted to Contract '{quotation.contract.contract_no}'.")

        if quotation.status not in [Quotation.Status.ACCEPTED, Quotation.Status.APPROVED_BY_MANAGEMENT]:
            raise ValidationError(f"Cannot convert quotation with status '{quotation.get_status_display()}'. Must be in 'Accepted' or 'Approved' status.")

        # Generate unique contract number
        current_year = timezone.now().year
        contract_count = RentalContract.objects.filter(contract_no__startswith=f"CNT-{current_year}-").count() + 1
        contract_no = f"CNT-{current_year}-{contract_count:04d}"

        # Determine primary equipment and rate for legacy field compatibility
        items = list(quotation.items.select_related('equipment').all())
        primary_equipment = items[0].equipment if items else None
        agreed_rate = items[0].rate_applied if items else Decimal('0.00')

        # Create Contract
        contract = RentalContract.objects.create(
            contract_no=contract_no,
            quotation=quotation,
            customer=quotation.customer,
            project_site=quotation.project_site,
            equipment=primary_equipment,
            contract_start_date=quotation.start_date,
            contract_end_date=quotation.end_date,
            billing_cycle=billing_cycle,
            agreed_rate=agreed_rate,
            deposit_paid=quotation.security_deposit_required,
            status=RentalContract.Status.ACTIVE
        )

        # Create RentalContractItem lines & transition all machinery to RESERVED
        for item in items:
            RentalContractItem.objects.create(
                contract=contract,
                equipment=item.equipment,
                start_date=item.item_start_date or quotation.start_date,
                end_date=item.item_end_date or quotation.end_date,
                rate_applied=item.rate_applied,
                rate_type=item.rate_type,
                subtotal_amount=item.subtotal_amount,
            )
            item.equipment.transition_status(
                Equipment.Status.RESERVED,
                user=user,
                notes=f"Reserved for Contract {contract.contract_no}"
            )

        # Mark Quotation as CONVERTED
        quotation.status = Quotation.Status.CONVERTED
        quotation.save(update_fields=['status', 'updated_at'])

        return contract


def process_equipment_dispatch(contract_id: str, dispatch_data: Dict[str, Any], user) -> DispatchReturn:
    """
    Executes machine mobilization handover.
    
    Step 4.2 State Machine Workflow:
    1. Creates DispatchReturn record with opening hour-meter, fuel level, checklist for the asset.
    2. Transitions Equipment.status -> ON_RENT.
    3. Transitions RentalContract.status -> ON_RENT.
    """
    with transaction.atomic():
        contract = RentalContract.objects.select_for_update().get(contract_no=contract_id)
        
        # Support specifying specific equipment or defaulting to contract primary asset
        equipment = dispatch_data.get('equipment')
        if not equipment and 'equipment_id' in dispatch_data:
            equipment = Equipment.objects.get(asset_code=dispatch_data['equipment_id'])
        if not equipment:
            equipment = contract.equipment or (contract.items.first().equipment if contract.items.exists() else None)

        if not equipment:
            raise ValidationError(f"No equipment asset found on Contract '{contract.contract_no}' for dispatch.")

        current_year = timezone.now().year
        trx_count = DispatchReturn.objects.filter(transaction_id__startswith=f"TRX-{current_year}-").count() + 1
        transaction_id = f"TRX-{current_year}-{trx_count:04d}"

        dispatch_datetime = dispatch_data.get('dispatch_datetime', timezone.now())
        dispatch_hour_meter = Decimal(str(dispatch_data.get('dispatch_hour_meter', equipment.current_hour_meter)))
        dispatch_fuel_level = Decimal(str(dispatch_data.get('dispatch_fuel_level', '100.00')))
        dispatch_checklist = dispatch_data.get('dispatch_checklist', {})

        # Create Dispatch record
        dispatch_record = DispatchReturn.objects.create(
            transaction_id=transaction_id,
            contract=contract,
            equipment=equipment,
            dispatch_datetime=dispatch_datetime,
            dispatch_hour_meter=dispatch_hour_meter,
            dispatch_fuel_level=dispatch_fuel_level,
            dispatch_officer=user,
            dispatch_checklist=dispatch_checklist
        )

        # Update Equipment status and hour meter
        equipment.current_hour_meter = dispatch_hour_meter
        equipment.transition_status(Equipment.Status.ON_RENT, user=user, notes=f"Dispatched under Contract {contract.contract_no}")
        equipment.save(update_fields=['current_hour_meter', 'updated_at'])

        # Update Contract status
        contract.status = RentalContract.Status.ON_RENT
        contract.save(update_fields=['status', 'updated_at'])

        return dispatch_record


def process_equipment_return(dispatch_return_id: str, return_data: Dict[str, Any], user) -> DispatchReturn:
    """
    Executes machine check-in and demobilization inspection.
    
    Step 4.2 State Machine Workflow:
    1. Records closing hour meter, return fuel level, inspection checklist.
    2. Computes excess hour meter usage against contract thresholds.
    3. If damage reported: Transitions Equipment.status -> MAINTENANCE (or BREAKDOWN); else -> AVAILABLE.
    4. Transitions RentalContract.status -> RETURNED.
    5. Placeholder: Automatic finance invoice calculation trigger for Step 5.
    """
    with transaction.atomic():
        dispatch_record = DispatchReturn.objects.select_for_update().get(transaction_id=dispatch_return_id)
        contract = dispatch_record.contract
        equipment = dispatch_record.equipment

        return_datetime = return_data.get('return_datetime', timezone.now())
        return_hour_meter = Decimal(str(return_data.get('return_hour_meter', equipment.current_hour_meter)))
        return_fuel_level = Decimal(str(return_data.get('return_fuel_level', '100.00')))
        return_checklist = return_data.get('return_checklist', {})
        damage_reported = bool(return_data.get('damage_reported', False))
        damage_notes = str(return_data.get('damage_notes', ''))

        # Calculate excess hours: Duration days * standard 8 hrs/day
        total_contract_days = contract.quotation.duration_days if contract.quotation else 1
        standard_allowance_hours = Decimal(str(total_contract_days * 8))
        actual_hours_used = max(Decimal('0.00'), return_hour_meter - dispatch_record.dispatch_hour_meter)
        excess_hours = max(Decimal('0.00'), actual_hours_used - standard_allowance_hours)

        # Update Dispatch & Return record
        dispatch_record.return_datetime = return_datetime
        dispatch_record.return_hour_meter = return_hour_meter
        dispatch_record.return_fuel_level = return_fuel_level
        dispatch_record.return_officer = user
        dispatch_record.return_checklist = return_checklist
        dispatch_record.damage_reported = damage_reported
        dispatch_record.damage_notes = damage_notes
        dispatch_record.excess_hours_calculated = excess_hours
        dispatch_record.save()

        # Update Equipment current meter reading
        equipment.current_hour_meter = return_hour_meter
        if damage_reported:
            equipment.transition_status(Equipment.Status.MAINTENANCE, user=user, notes=f"Returned with damages from Contract {contract.contract_no}: {damage_notes}")
        else:
            equipment.transition_status(Equipment.Status.AVAILABLE, user=user, notes=f"Returned in good order from Contract {contract.contract_no}")
        equipment.save(update_fields=['current_hour_meter', 'updated_at'])

        # Update Contract status
        contract.status = RentalContract.Status.RETURNED
        contract.save(update_fields=['status', 'updated_at'])

        # --- Automated Finance Integration Hook ---
        # Note: Step 5 Billing Engine will invoke generate_final_rental_invoice(contract.contract_no, user)

        return dispatch_record
