"""
Rentals Calendar API & Availability Conflict Engine
Reference: docs/23_PHASE_1_ROADMAP.md (Step 6.1)
"""

from datetime import datetime, timedelta
from decimal import Decimal
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.urls import reverse
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin

from fleet.models import Equipment, Category
from fleet.managers import get_available_equipment
from rentals.models import RentalContract, Quotation


class CalendarEventsAPIView(LoginRequiredMixin, View):
    """
    JSON API endpoint returning timeline schedule events for FullCalendar.
    Route: /api/v1/rentals/calendar-events/ and /rentals/api/calendar-events/
    """

    def get(self, request, *args, **kwargs):
        start_str = request.GET.get('start', '').strip()
        end_str = request.GET.get('end', '').strip()
        category_id = request.GET.get('category', '').strip()
        equipment_code = request.GET.get('equipment', '').strip()
        status_filter = request.GET.get('status', '').strip()

        # Parse start and end date bounds (FullCalendar passes ISO date/datetime)
        try:
            if start_str:
                start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00')).date()
            else:
                start_date = timezone.now().date() - timedelta(days=30)
        except Exception:
            start_date = timezone.now().date() - timedelta(days=30)

        try:
            if end_str:
                end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00')).date()
            else:
                end_date = timezone.now().date() + timedelta(days=60)
        except Exception:
            end_date = timezone.now().date() + timedelta(days=60)

        events = []

        # 1. On Rent (Active / Dispatched Rental Contracts) — Blue (#0d6efd)
        if not status_filter or status_filter in ['ALL', 'ON_RENT']:
            contract_qs = RentalContract.objects.select_related(
                'equipment', 'equipment__category', 'customer', 'project_site'
            ).filter(
                status__in=['ACTIVE', 'ON_RENT', 'DISPATCHED', 'PENDING_RETURN'],
                contract_start_date__lte=end_date,
                contract_end_date__gte=start_date
            )

            if category_id:
                contract_qs = contract_qs.filter(equipment__category_id=category_id)
            if equipment_code:
                contract_qs = contract_qs.filter(equipment__asset_code=equipment_code)

            for contract in contract_qs:
                c_end = contract.contract_end_date + timedelta(days=1)
                events.append({
                    'id': f"contract-{contract.contract_no}",
                    'title': f"[{contract.equipment.asset_code}] On Rent: {contract.contract_no} ({contract.customer.company_name})",
                    'start': contract.contract_start_date.isoformat(),
                    'end': c_end.isoformat(),
                    'allDay': True,
                    'backgroundColor': '#0d6efd',
                    'borderColor': '#0b5ed7',
                    'textColor': '#ffffff',
                    'url': reverse('rentals:contract_detail', kwargs={'contract_no': contract.contract_no}),
                    'extendedProps': {
                        'type': 'ON_RENT',
                        'type_display': 'On Rent (Contract)',
                        'badge_class': 'bg-primary',
                        'asset_code': contract.equipment.asset_code,
                        'equipment_name': contract.equipment.equipment_name,
                        'category': contract.equipment.category.name if contract.equipment.category else '',
                        'customer_name': contract.customer.company_name,
                        'project_site': contract.project_site.project_name,
                        'contract_no': contract.contract_no,
                        'start_date': contract.contract_start_date.strftime('%Y-%m-%d'),
                        'end_date': contract.contract_end_date.strftime('%Y-%m-%d'),
                        'status': contract.get_status_display(),
                        'agreed_rate': float(contract.agreed_rate) if contract.agreed_rate else 0.0,
                    }
                })

        # 2. Reserved (Approved / Accepted Quotations) — Yellow (#ffc107)
        if not status_filter or status_filter in ['ALL', 'RESERVED']:
            quote_qs = Quotation.objects.select_related(
                'equipment', 'equipment__category', 'customer', 'project_site'
            ).filter(
                status__in=['APPROVED_BY_MANAGEMENT', 'SENT_TO_CUSTOMER', 'ACCEPTED'],
                start_date__lte=end_date,
                end_date__gte=start_date
            ).filter(contract__isnull=True)

            if category_id:
                quote_qs = quote_qs.filter(equipment__category_id=category_id)
            if equipment_code:
                quote_qs = quote_qs.filter(equipment__asset_code=equipment_code)

            for quote in quote_qs:
                q_end = quote.end_date + timedelta(days=1)
                events.append({
                    'id': f"quote-{quote.quotation_no}",
                    'title': f"[{quote.equipment.asset_code}] Reserved: {quote.quotation_no} ({quote.customer.company_name})",
                    'start': quote.start_date.isoformat(),
                    'end': q_end.isoformat(),
                    'allDay': True,
                    'backgroundColor': '#ffc107',
                    'borderColor': '#d39e00',
                    'textColor': '#000000',
                    'url': reverse('rentals:quotation_detail', kwargs={'quotation_no': quote.quotation_no}),
                    'extendedProps': {
                        'type': 'RESERVED',
                        'type_display': 'Reserved (Quotation)',
                        'badge_class': 'bg-warning text-dark',
                        'asset_code': quote.equipment.asset_code,
                        'equipment_name': quote.equipment.equipment_name,
                        'category': quote.equipment.category.name if quote.equipment.category else '',
                        'customer_name': quote.customer.company_name,
                        'project_site': quote.project_site.project_name,
                        'quotation_no': quote.quotation_no,
                        'start_date': quote.start_date.strftime('%Y-%m-%d'),
                        'end_date': quote.end_date.strftime('%Y-%m-%d'),
                        'status': quote.get_status_display(),
                        'daily_rate': float(quote.rate_applied) if quote.rate_applied else 0.0,
                    }
                })

        # 3. Maintenance / Breakdown — Red (#dc3545)
        if not status_filter or status_filter in ['ALL', 'MAINTENANCE']:
            maint_qs = Equipment.objects.select_related('category').filter(
                status__in=['MAINTENANCE', 'BREAKDOWN']
            )

            if category_id:
                maint_qs = maint_qs.filter(category_id=category_id)
            if equipment_code:
                maint_qs = maint_qs.filter(asset_code=equipment_code)

            today = timezone.now().date()
            maint_end = today + timedelta(days=14)

            for eq in maint_qs:
                events.append({
                    'id': f"maint-{eq.asset_code}",
                    'title': f"[{eq.asset_code}] {eq.get_status_display()}: {eq.equipment_name}",
                    'start': today.isoformat(),
                    'end': maint_end.isoformat(),
                    'allDay': True,
                    'backgroundColor': '#dc3545',
                    'borderColor': '#b02a37',
                    'textColor': '#ffffff',
                    'url': reverse('fleet:equipment_detail', kwargs={'asset_code': eq.asset_code}),
                    'extendedProps': {
                        'type': 'MAINTENANCE',
                        'type_display': eq.get_status_display(),
                        'badge_class': 'bg-danger',
                        'asset_code': eq.asset_code,
                        'equipment_name': eq.equipment_name,
                        'category': eq.category.name if eq.category else '',
                        'customer_name': 'In-House Workshop',
                        'project_site': 'Central Yard Maintenance Bay',
                        'start_date': today.strftime('%Y-%m-%d'),
                        'end_date': maint_end.strftime('%Y-%m-%d'),
                        'status': eq.get_status_display(),
                    }
                })

        # 4. Equipment Available Windows (When requested via AVAILABLE filter or specific asset) — Green (#198754)
        if status_filter == 'AVAILABLE' or (equipment_code and not status_filter):
            avail_qs = Equipment.objects.select_related('category').filter(status='AVAILABLE')
            if category_id:
                avail_qs = avail_qs.filter(category_id=category_id)
            if equipment_code:
                avail_qs = avail_qs.filter(asset_code=equipment_code)

            for eq in avail_qs:
                events.append({
                    'id': f"avail-{eq.asset_code}",
                    'title': f"[{eq.asset_code}] Available: {eq.equipment_name}",
                    'start': start_date.isoformat(),
                    'end': (end_date + timedelta(days=1)).isoformat(),
                    'allDay': True,
                    'backgroundColor': '#198754',
                    'borderColor': '#146c43',
                    'textColor': '#ffffff',
                    'url': reverse('fleet:equipment_detail', kwargs={'asset_code': eq.asset_code}),
                    'extendedProps': {
                        'type': 'AVAILABLE',
                        'type_display': 'Ready for Dispatch',
                        'badge_class': 'bg-success',
                        'asset_code': eq.asset_code,
                        'equipment_name': eq.equipment_name,
                        'category': eq.category.name if eq.category else '',
                        'customer_name': 'Central Equipment Yard',
                        'project_site': 'Ready Inventory',
                        'start_date': start_date.strftime('%Y-%m-%d'),
                        'end_date': end_date.strftime('%Y-%m-%d'),
                        'status': 'Available',
                    }
                })

        return JsonResponse(events, safe=False)


class EquipmentAvailabilityCheckAPIView(LoginRequiredMixin, View):
    """
    API endpoint to check real-time availability of equipment assets
    for given dates and machinery category with conflict overlap detection.
    """

    def get(self, request, *args, **kwargs):
        category_id = request.GET.get('category_id') or request.GET.get('category')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        if not start_date:
            start_date = timezone.now().date()
        if not end_date:
            end_date = start_date + timedelta(days=1)

        available_qs = get_available_equipment(
            category_id=category_id if category_id else None,
            start_date=start_date,
            end_date=end_date
        ).select_related('category').prefetch_related('rental_rates')

        results = []
        for eq in available_qs:
            rate_card = eq.rental_rates.filter(is_active=True).first()
            daily_rate = float(rate_card.daily_rate) if rate_card and rate_card.daily_rate else 0.0
            weekly_rate = float(rate_card.weekly_rate) if rate_card and rate_card.weekly_rate else 0.0
            monthly_rate = float(rate_card.monthly_rate) if rate_card and rate_card.monthly_rate else 0.0

            create_quote_url = f"{reverse('rentals:quotation_create')}?equipment={eq.asset_code}&start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"

            results.append({
                'asset_code': eq.asset_code,
                'equipment_name': eq.equipment_name,
                'category_name': eq.category.name if eq.category else 'General Machinery',
                'brand': eq.brand,
                'model_number': eq.model_number,
                'daily_rate': daily_rate,
                'weekly_rate': weekly_rate,
                'monthly_rate': monthly_rate,
                'current_hour_meter': float(eq.current_hour_meter),
                'photo_url': eq.primary_image.url if eq.primary_image else None,
                'create_quote_url': create_quote_url,
                'detail_url': reverse('fleet:equipment_detail', kwargs={'asset_code': eq.asset_code}),
            })

        return JsonResponse({
            'success': True,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_available': len(results),
            'equipment': results
        })
