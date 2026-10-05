"""
CERMS - Rentals Business Services Layer
Handles Customer credit checks, quotation lifecycle, and contract logic.
Reference: docs/04_BUSINESS_WORKFLOWS.md & docs/23_PHASE_1_ROADMAP.md
"""

from decimal import Decimal
from typing import Dict, Any, Union
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Customer


def validate_customer_credit_limit(customer: Customer, new_quotation_amount: Union[Decimal, float, int]) -> Dict[str, Any]:
    """
    Validates whether a new rental engagement exceeds the customer's allocated credit limit
    or if the commercial account is in a blocked/suspended status.

    Args:
        customer (Customer): The customer instance being assessed.
        new_quotation_amount (Decimal): Total monetary value of the new rental engagement.

    Returns:
        Dict[str, Any]: Detailed evaluation payload including approval requirement flag.
    """
    amount = Decimal(str(new_quotation_amount))
    outstanding = customer.current_outstanding_balance
    limit = customer.credit_limit
    projected = outstanding + amount

    # Check 1: Inactive or Blocked Status
    if customer.status == Customer.Status.BLOCKED:
        return {
            'is_valid': False,
            'requires_approval': True,
            'message': _(f"Customer account '{customer.customer_code}' is currently ON CREDIT HOLD / BLOCKED."),
            'outstanding_balance': outstanding,
            'credit_limit': limit,
            'projected_balance': projected,
            'exceeded_by': projected - limit if projected > limit else Decimal('0.00'),
        }

    if customer.status == Customer.Status.INACTIVE:
        return {
            'is_valid': False,
            'requires_approval': True,
            'message': _(f"Customer account '{customer.customer_code}' is marked INACTIVE."),
            'outstanding_balance': outstanding,
            'credit_limit': limit,
            'projected_balance': projected,
            'exceeded_by': Decimal('0.00'),
        }

    # Check 2: Zero Credit Limit (Prepayment Required)
    if limit == Decimal('0.00'):
        return {
            'is_valid': True,
            'requires_approval': False,
            'message': _("Customer has standard prepayment terms (Zero Credit Line)."),
            'outstanding_balance': outstanding,
            'credit_limit': limit,
            'projected_balance': projected,
            'exceeded_by': Decimal('0.00'),
        }

    # Check 3: Credit Limit Exceeded
    if projected > limit:
        exceeded_amount = projected - limit
        return {
            'is_valid': False,
            'requires_approval': True,
            'message': _(
                f"Credit limit exceeded by Rs. {exceeded_amount:,.2f}. "
                f"Outstanding: Rs. {outstanding:,.2f} + New: Rs. {amount:,.2f} > Limit: Rs. {limit:,.2f}. "
                f"Requires Executive Management approval."
            ),
            'outstanding_balance': outstanding,
            'credit_limit': limit,
            'projected_balance': projected,
            'exceeded_by': exceeded_amount,
        }

    # Passed Check
    return {
        'is_valid': True,
        'requires_approval': False,
        'message': _("Customer credit check passed successfully."),
        'outstanding_balance': outstanding,
        'credit_limit': limit,
        'projected_balance': projected,
        'exceeded_by': Decimal('0.00'),
    }
