"""
Fleet Managers & Equipment Availability QuerySet
Reference: docs/23_PHASE_1_ROADMAP.md (Step 6.1)
"""

from django.db import models
from django.utils import timezone


class EquipmentQuerySet(models.QuerySet):
    """Custom queryset providing helper methods for fleet availability and filtering."""

    def available(self):
        """Returns equipment physically available for rental."""
        return self.filter(status='AVAILABLE')

    def on_rent(self):
        """Returns equipment currently deployed on active rental contracts."""
        return self.filter(status='ON_RENT')

    def maintenance(self):
        """Returns equipment currently in maintenance or breakdown."""
        return self.filter(status__in=['MAINTENANCE', 'BREAKDOWN'])

    def available_for_dates(self, start_date, end_date, category_id=None, exclude_contract_id=None, exclude_quotation_id=None):
        """
        Returns equipment that are AVAILABLE and have no conflicting contracts
        (single-asset or multi-asset RentalContractItem) or reserved quotations
        (QuotationItem in APPROVED_BY_MANAGEMENT, SENT_TO_CUSTOMER, ACCEPTED status)
        for the given start_date and end_date.
        """
        from datetime import date, datetime
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return self.none()
        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return self.none()

        from django.apps import apps
        from django.db.models import Q

        RentalContract = apps.get_model('rentals', 'RentalContract')
        RentalContractItem = apps.get_model('rentals', 'RentalContractItem')
        QuotationItem = apps.get_model('rentals', 'QuotationItem')

        qs = self.filter(status='AVAILABLE')
        if category_id:
            qs = qs.filter(category_id=category_id)

        if start_date and end_date and start_date <= end_date:
            # 1. Direct single-asset active contracts
            direct_contracts = RentalContract.objects.filter(
                equipment__isnull=False,
                status__in=['ACTIVE', 'ON_RENT', 'DISPATCHED'],
                contract_start_date__lte=end_date,
                contract_end_date__gte=start_date
            )
            if exclude_contract_id:
                c_pk = exclude_contract_id.pk if hasattr(exclude_contract_id, 'pk') else exclude_contract_id
                direct_contracts = direct_contracts.exclude(pk=c_pk)
            conflicting_direct = list(direct_contracts.values_list('equipment_id', flat=True))

            # 2. Multi-asset active contract items
            contract_items = RentalContractItem.objects.filter(
                contract__status__in=['ACTIVE', 'ON_RENT', 'DISPATCHED']
            ).filter(
                (Q(start_date__isnull=False) & Q(end_date__isnull=False) & Q(start_date__lte=end_date, end_date__gte=start_date)) |
                ((Q(start_date__isnull=True) | Q(end_date__isnull=True)) & Q(contract__contract_start_date__lte=end_date, contract__contract_end_date__gte=start_date))
            )
            if exclude_contract_id:
                c_pk = exclude_contract_id.pk if hasattr(exclude_contract_id, 'pk') else exclude_contract_id
                contract_items = contract_items.exclude(contract__pk=c_pk)
            conflicting_items = list(contract_items.values_list('equipment_id', flat=True))

            # 3. Reserved quotations (APPROVED_BY_MANAGEMENT, SENT_TO_CUSTOMER, ACCEPTED)
            q_item_dates = (
                (Q(start_date__isnull=False) & Q(end_date__isnull=False) & Q(start_date__lte=end_date, end_date__gte=start_date)) |
                ((Q(start_date__isnull=True) | Q(end_date__isnull=True)) & Q(quotation__start_date__lte=end_date, quotation__end_date__gte=start_date))
            )
            quotation_items = QuotationItem.objects.filter(
                quotation__status__in=['APPROVED_BY_MANAGEMENT', 'SENT_TO_CUSTOMER', 'ACCEPTED'],
                quotation__contract__isnull=True
            ).filter(q_item_dates)
            if exclude_quotation_id:
                q_pk = exclude_quotation_id.pk if hasattr(exclude_quotation_id, 'pk') else exclude_quotation_id
                quotation_items = quotation_items.exclude(quotation__pk=q_pk)
            conflicting_quotes = list(quotation_items.values_list('equipment_id', flat=True))

            conflicting_assets = set(filter(None, conflicting_direct + conflicting_items + conflicting_quotes))
            qs = qs.exclude(pk__in=conflicting_assets)

        return qs


class EquipmentManager(models.Manager.from_queryset(EquipmentQuerySet)):
    """Default Manager for Equipment assets."""
    pass


def get_available_equipment(category_id=None, start_date=None, end_date=None, exclude_contract_id=None, exclude_quotation_id=None):
    """
    Overlap Detection Query finding equipment free of active contracts
    (single-asset and multi-asset RentalContractItem), reserved quotations
    (QuotationItem in APPROVED_BY_MANAGEMENT, SENT_TO_CUSTOMER, ACCEPTED),
    and maintenance for the specified date window and optional machinery category.
    Reference: docs/23_PHASE_1_ROADMAP.md (Step 6.1)
    """
    from django.apps import apps
    Equipment = apps.get_model('fleet', 'Equipment')

    return Equipment.objects.available_for_dates(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        exclude_contract_id=exclude_contract_id,
        exclude_quotation_id=exclude_quotation_id
    )
