from decimal import Decimal
from typing import Dict, Any
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Customer


def validate_customer_credit_limit(customer: Customer, new_quotation_amount: Decimal, raise_exception: bool = False) -> Dict[str, Any]:
    """
    Evaluates customer creditworthiness, operational standing, and outstanding balance against
    their approved credit ceiling.

    Args:
        customer (Customer): The customer entity requesting a new rental quotation.
        new_quotation_amount (Decimal): The monetary value (LKR) of the prospective contract/quotation.
        raise_exception (bool): When True, raises a Django ValidationError upon critical policy violation.

    Returns:
        dict: Detailed audit dictionary with approval status, remaining limits, and management flags:
            {
                'is_approved': bool,
                'requires_management_override': bool,
                'customer_code': str,
                'customer_status': str,
                'credit_limit': Decimal,
                'current_outstanding_balance': Decimal,
                'new_quotation_amount': Decimal,
                'projected_total_exposure': Decimal,
                'excess_amount': Decimal,
                'message': str
            }
    """
    amount = Decimal(str(new_quotation_amount))
    current_balance = Decimal(str(customer.current_outstanding_balance))
    credit_limit = Decimal(str(customer.credit_limit))
    projected_exposure = current_balance + amount

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
            'requires_management_override': True,
            'customer_code': customer.customer_code,
            'customer_status': customer.status,
            'credit_limit': credit_limit,
            'current_outstanding_balance': current_balance,
            'new_quotation_amount': amount,
            'projected_total_exposure': projected_exposure,
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
            'requires_management_override': True,
            'customer_code': customer.customer_code,
            'customer_status': customer.status,
            'credit_limit': credit_limit,
            'current_outstanding_balance': current_balance,
            'new_quotation_amount': amount,
            'projected_total_exposure': projected_exposure,
            'excess_amount': excess,
            'message': str(warning_msg)
        }

    # 3. Credit Approved
    remaining_margin = credit_limit - projected_exposure if credit_limit > Decimal('0.00') else Decimal('0.00')
    success_msg = _(
        f"Credit validation passed for '{customer.company_name}'. "
        f"Projected exposure (LKR {projected_exposure:,.2f}) is within approved credit limits."
    )
    return {
        'is_approved': True,
        'requires_management_override': False,
        'customer_code': customer.customer_code,
        'customer_status': customer.status,
        'credit_limit': credit_limit,
        'current_outstanding_balance': current_balance,
        'new_quotation_amount': amount,
        'projected_total_exposure': projected_exposure,
        'excess_amount': Decimal('0.00'),
        'remaining_available_margin': remaining_margin,
        'message': str(success_msg)
    }
