from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from fleet.models import Category, Equipment, RentalRate


class FleetModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Excavator',
            code='EXC',
            description='Heavy earthmoving machinery'
        )
        self.equipment = Equipment.objects.create(
            asset_code='EQ-CAT-320-001',
            equipment_name='Caterpillar 320D Hydraulic Excavator',
            category=self.category,
            brand='Caterpillar',
            model_number='320D',
            serial_number='CAT320D-2026-X1',
            manufacture_year=2022,
            purchase_cost=Decimal('28500000.00'),
            purchase_date=timezone.now().date(),
            current_hour_meter=Decimal('1450.50'),
            status=Equipment.Status.AVAILABLE
        )
        self.rate = RentalRate.objects.create(
            equipment=self.equipment,
            daily_rate=Decimal('45000.00'),
            hourly_rate=Decimal('6000.00'),
            weekly_rate=Decimal('280000.00'),
            monthly_rate=Decimal('1100000.00'),
            overtime_hourly_rate=Decimal('7500.00'),
            minimum_rental_hours=8,
            is_active=True
        )

    def test_equipment_creation_and_properties(self):
        self.assertEqual(str(self.category), "Excavator (EXC)")
        self.assertTrue(self.equipment.is_available)
        self.assertEqual(self.equipment.rental_rates.count(), 1)

    def test_status_transition(self):
        self.equipment.transition_status(Equipment.Status.MAINTENANCE, notes="Scheduled 1500h service")
        self.assertEqual(self.equipment.status, Equipment.Status.MAINTENANCE)
        self.assertFalse(self.equipment.is_available)

    def test_invalid_status_transition_raises_error(self):
        with self.assertRaises(ValueError):
            self.equipment.transition_status("INVALID_STATUS")
