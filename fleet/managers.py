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

    def available_for_dates(self, start_date, end_date, category_id=None):
        """
        Returns equipment that are AVAILABLE and have no conflicting contracts
        for the given start_date and end_date.
        """
        from django.apps import apps
        RentalContract = apps.get_model('rentals', 'RentalContract')

        qs = self.filter(status='AVAILABLE')
        if category_id:
            qs = qs.filter(category_id=category_id)

        if start_date and end_date:
            conflicting_contracts = RentalContract.objects.filter(
                status__in=['ACTIVE', 'ON_RENT', 'DISPATCHED'],
                contract_start_date__lte=end_date,
                contract_end_date__gte=start_date
            ).values_list('equipment_id', flat=True)

            qs = qs.exclude(asset_code__in=conflicting_contracts)

        return qs


class EquipmentManager(models.Manager.from_queryset(EquipmentQuerySet)):
    """Default Manager for Equipment assets."""
    pass


def get_available_equipment(category_id=None, start_date=None, end_date=None):
    """
    Overlap Detection Query finding equipment free of active contracts
    and maintenance for the specified date window and optional machinery category.
    Reference: docs/23_PHASE_1_ROADMAP.md (Step 6.1)
    """
    from django.apps import apps
    Equipment = apps.get_model('fleet', 'Equipment')
    RentalContract = apps.get_model('rentals', 'RentalContract')

    qs = Equipment.objects.filter(status='AVAILABLE')
    if category_id:
        qs = qs.filter(category_id=category_id)

    if start_date and end_date:
        conflicting_contracts = RentalContract.objects.filter(
            status__in=['ACTIVE', 'ON_RENT', 'DISPATCHED'],
            contract_start_date__lte=end_date,
            contract_end_date__gte=start_date
        ).values_list('equipment_id', flat=True)

        return qs.exclude(asset_code__in=conflicting_contracts)

    return qs
