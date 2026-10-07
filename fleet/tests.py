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


class CategoryViewTests(TestCase):
    def setUp(self):
        from users.models import User
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='AdminPass123!',
            role=User.Role.ADMINISTRATOR
        )
        self.workshop_user = User.objects.create_user(
            username='workshop_test',
            email='workshop@test.com',
            password='StaffPass123!',
            role=User.Role.WORKSHOP_MANAGER
        )
        self.field_officer = User.objects.create_user(
            username='field_test',
            email='field@test.com',
            password='StaffPass123!',
            role=User.Role.FIELD_OFFICER
        )
        self.category = Category.objects.create(
            name='Cranes',
            code='CRN',
            description='Mobile & Crawler Cranes'
        )

    def test_category_list_view_authenticated(self):
        self.client.force_login(self.workshop_user)
        response = self.client.get('/fleet/categories/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/category_list.html')
        self.assertContains(response, 'Cranes')
        self.assertContains(response, 'CRN')

    def test_category_create_view_by_workshop_manager(self):
        self.client.force_login(self.workshop_user)
        # GET form
        response = self.client.get('/fleet/categories/create/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/category_form.html')

        # POST valid category
        post_data = {
            'name': 'Generators & Power',
            'code': 'gen',
            'description': 'Industrial diesel generators'
        }
        post_response = self.client.post('/fleet/categories/create/', data=post_data)
        self.assertEqual(post_response.status_code, 302)
        self.assertRedirects(post_response, '/fleet/categories/')
        self.assertTrue(Category.objects.filter(code='GEN').exists())

    def test_category_update_view(self):
        self.client.force_login(self.admin_user)
        update_data = {
            'name': 'Heavy Mobile Cranes',
            'code': 'CRN',
            'description': 'Updated crawler and mobile cranes'
        }
        response = self.client.post(f'/fleet/categories/{self.category.code}/edit/', data=update_data)
        self.assertEqual(response.status_code, 302)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Heavy Mobile Cranes')

    def test_category_create_restricted_for_unauthorized_role(self):
        self.client.force_login(self.field_officer)
        response = self.client.get('/fleet/categories/create/')
        # Field officer should be denied with 403 Forbidden
        self.assertEqual(response.status_code, 403)

    def test_category_auto_code_generation_algorithm(self):
        # 1. Test model-level generator method
        code_exc = Category.generate_code_from_name("Hydraulic Excavators")
        self.assertEqual(code_exc, "HEXC")

        code_gen = Category.generate_code_from_name("Generators & Power")
        self.assertEqual(code_gen, "GENP")

        code_hem = Category.generate_code_from_name("Heavy Earth Moving")
        self.assertEqual(code_hem, "HEM")

        # 2. Test auto-code creation via form with blank code
        self.client.force_login(self.workshop_user)
        post_data = {
            'name': 'Compaction Rollers',
            'code': '',  # Left blank to test auto-generation
            'description': 'Smooth drum and padfoot rollers'
        }
        res = self.client.post('/fleet/categories/create/', data=post_data)
        self.assertEqual(res.status_code, 302)
        cat = Category.objects.get(name='Compaction Rollers')
        self.assertEqual(cat.code, 'CORO')

        # 3. Test uniqueness disambiguation
        code_collision = Category.generate_code_from_name("Compaction Rollers")
        self.assertTrue(code_collision.startswith('CORO-'))


