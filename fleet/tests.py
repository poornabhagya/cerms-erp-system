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
        self.assertEqual(code_exc, "HYEX")

        code_gen = Category.generate_code_from_name("Generators & Power")
        self.assertEqual(code_gen, "GEPO")

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


class EquipmentAssetCodeGenerationTests(TestCase):
    def setUp(self):
        from users.models import User
        self.workshop_user = User.objects.create_user(
            username='workshop_tester',
            email='workshop_tester@test.com',
            password='StaffPass123!',
            role=User.Role.WORKSHOP_MANAGER
        )
        self.category_exc = Category.objects.create(
            name='Hydraulic Excavators',
            code='EXC',
            description='Excavators'
        )

    def test_asset_code_generation_format_and_sequence(self):
        # 1. First asset for Category EXC, Brand Caterpillar, Model 320D
        code_1 = Equipment.generate_asset_code(
            category=self.category_exc,
            brand="Caterpillar",
            model_number="320D"
        )
        self.assertEqual(code_1, "EQ-EXC-CAT-320D-001")

        # Save an equipment asset with code_1
        Equipment.objects.create(
            asset_code=code_1,
            equipment_name="CAT 320D Excavator #1",
            category=self.category_exc,
            brand="Caterpillar",
            model_number="320D",
            serial_number="SER-CAT-001",
            manufacture_year=2023,
            purchase_cost=Decimal("35000000.00"),
            purchase_date=timezone.now().date(),
            current_hour_meter=Decimal("100.00"),
            status=Equipment.Status.AVAILABLE
        )

        # 2. Second asset for same category, brand, and model should increment sequence to 002
        code_2 = Equipment.generate_asset_code(
            category=self.category_exc,
            brand="Caterpillar",
            model_number="320D"
        )
        self.assertEqual(code_2, "EQ-EXC-CAT-320D-002")

    def test_asset_code_api_endpoint(self):
        self.client.force_login(self.workshop_user)
        response = self.client.get(
            f'/fleet/api/generate-asset-code/?category_id={self.category_exc.id}&brand=Komatsu&model_number=PC200'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['asset_code'], "EQ-EXC-KOM-PC200-001")


class EquipmentDeleteAndSpecsTests(TestCase):
    def setUp(self):
        from users.models import User
        self.admin_user = User.objects.create_superuser(
            username='admin_delete_tester',
            email='admin_del@test.com',
            password='AdminPass123!',
            role=User.Role.ADMINISTRATOR
        )
        self.workshop_user = User.objects.create_user(
            username='workshop_delete_tester',
            email='workshop_del@test.com',
            password='StaffPass123!',
            role=User.Role.WORKSHOP_MANAGER
        )
        self.field_user = User.objects.create_user(
            username='field_delete_tester',
            email='field_del@test.com',
            password='StaffPass123!',
            role=User.Role.FIELD_OFFICER
        )
        self.category = Category.objects.create(
            name='Bulldozers',
            code='BLD',
            description='Track dozers'
        )
        self.equipment = Equipment.objects.create(
            asset_code='EQ-BLD-CAT-D6T-001',
            equipment_name='CAT D6T Track-Type Tractor',
            category=self.category,
            brand='Caterpillar',
            model_number='D6T',
            serial_number='CAT-D6T-999',
            manufacture_year=2021,
            purchase_cost=Decimal('42000000.00'),
            purchase_date=timezone.now().date(),
            current_hour_meter=Decimal('850.00'),
            specifications={"Operating Weight": "21500 kg", "Blade Capacity": "4.5 m3"},
            status=Equipment.Status.AVAILABLE
        )

    def test_admin_can_delete_unlinked_equipment(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(f'/fleet/{self.equipment.asset_code}/delete/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/fleet/')
        self.assertFalse(Equipment.objects.filter(asset_code='EQ-BLD-CAT-D6T-001').exists())

    def test_non_admin_cannot_delete_equipment(self):
        # Workshop manager should be denied (403)
        self.client.force_login(self.workshop_user)
        response = self.client.post(f'/fleet/{self.equipment.asset_code}/delete/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Equipment.objects.filter(asset_code='EQ-BLD-CAT-D6T-001').exists())

        # Field officer should be denied (403)
        self.client.force_login(self.field_user)
        response2 = self.client.post(f'/fleet/{self.equipment.asset_code}/delete/')
        self.assertEqual(response2.status_code, 403)
        self.assertTrue(Equipment.objects.filter(asset_code='EQ-BLD-CAT-D6T-001').exists())

    def test_delete_blocked_when_linked_to_quotation(self):
        from rentals.models import Customer, ProjectSite, Quotation, QuotationItem
        import datetime
        customer = Customer.objects.create(
            customer_code='CUST-2026-888',
            company_name='Mega Infra Ltd',
            contact_person='John Builder',
            phone='0771234567',
            email='megainfra@test.com',
            billing_address='Colombo 02',
            vat_tax_number='T12345678'
        )
        site = ProjectSite.objects.create(
            project_code='PRJ-MEGA-01',
            customer=customer,
            project_name='Highway Extension',
            site_address='Kandy',
            status=ProjectSite.Status.ACTIVE
        )
        quotation = Quotation.objects.create(
            quotation_no='QT-2026-9999',
            customer=customer,
            project_site=site,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + datetime.timedelta(days=10),
            status=Quotation.Status.DRAFT,
        )
        QuotationItem.objects.create(
            quotation=quotation,
            equipment=self.equipment,
            rate_applied=Decimal('50000.00'),
            start_date=quotation.start_date,
            end_date=quotation.end_date,
        )

        self.client.force_login(self.admin_user)
        response = self.client.post(f'/fleet/{self.equipment.asset_code}/delete/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/fleet/{self.equipment.asset_code}/')
        # Equipment must still exist in DB
        self.assertTrue(Equipment.objects.filter(asset_code=self.equipment.asset_code).exists())

    def test_equipment_form_specifications_cleaner(self):
        from fleet.forms import EquipmentForm
        form_data = {
            'asset_code': 'EQ-BLD-KOM-D85-001',
            'equipment_name': 'Komatsu D85 Dozer',
            'category': self.category.id,
            'brand': 'Komatsu',
            'model_number': 'D85',
            'serial_number': 'KOM-D85-111',
            'manufacture_year': 2022,
            'purchase_cost': '38000000.00',
            'purchase_date': timezone.now().date(),
            'current_hour_meter': '500.00',
            'specifications': '{"Engine Power": "260 HP", "Blade Capacity": "5.2 m3", "": "Ignored"}',
            'status': 'AVAILABLE'
        }
        form = EquipmentForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        cleaned_specs = form.cleaned_data['specifications']
        self.assertEqual(cleaned_specs, {"Engine Power": "260 HP", "Blade Capacity": "5.2 m3"})



