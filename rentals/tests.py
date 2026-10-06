from datetime import date, datetime
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from users.models import User
from fleet.models import Category, Equipment
from .models import Customer, ProjectSite, Quotation, RentalContract, DispatchReturn
from .services import validate_customer_credit_limit, calculate_quotation_totals
from .forms import QuotationForm


class CustomerModelTestCase(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_code="CUST-2026-001",
            company_name="Access Engineering PLC",
            contact_person="Sunil Perera",
            phone="+94771234567",
            email="sunil@accesseng.lk",
            billing_address="No. 120, Station Road, Colombo 03",
            vat_tax_number="VAT-123456789",
            credit_limit=Decimal("1000000.00"),
            current_outstanding_balance=Decimal("250000.00"),
            status=Customer.Status.ACTIVE
        )

        self.site = ProjectSite.objects.create(
            project_code="PRJ-COL-001",
            customer=self.customer,
            project_name="Central Expressway Section III",
            site_address="Mirigama Interchange Site",
            gps_coordinates="7.2431,80.1294",
            site_contact_person="Kamal Silva",
            site_contact_phone="+94779876543",
            status=ProjectSite.Status.ACTIVE
        )

    def test_customer_creation_and_properties(self):
        self.assertEqual(str(self.customer), "CUST-2026-001 - Access Engineering PLC (Active)")
        self.assertTrue(self.customer.is_eligible_for_rentals)
        self.assertEqual(self.customer.available_credit, Decimal("750000.00"))

    def test_project_site_creation(self):
        self.assertEqual(str(self.site), "PRJ-COL-001 - Central Expressway Section III (Access Engineering PLC)")
        self.assertEqual(self.site.customer, self.customer)
        self.assertEqual(self.customer.project_sites.count(), 1)

    def test_validate_credit_limit_within_bounds(self):
        result = validate_customer_credit_limit(self.customer, Decimal("500000.00"))
        self.assertTrue(result['is_approved'])
        self.assertFalse(result['requires_management_override'])
        self.assertEqual(result['projected_total_exposure'], Decimal("750000.00"))
        self.assertEqual(result['remaining_available_margin'], Decimal("250000.00"))

    def test_validate_credit_limit_exceeded(self):
        # 250,000 + 800,000 = 1,050,000 > 1,000,000
        result = validate_customer_credit_limit(self.customer, Decimal("800000.00"))
        self.assertFalse(result['is_approved'])
        self.assertTrue(result['requires_management_override'])
        self.assertEqual(result['excess_amount'], Decimal("50000.00"))

    def test_validate_credit_limit_raises_exception_when_configured(self):
        with self.assertRaises(ValidationError):
            validate_customer_credit_limit(self.customer, Decimal("800000.00"), raise_exception=True)

    def test_validate_credit_limit_blocked_customer(self):
        self.customer.status = Customer.Status.BLOCKED
        self.customer.save()

        result = validate_customer_credit_limit(self.customer, Decimal("10000.00"))
        self.assertFalse(result['is_approved'])
        self.assertTrue(result['requires_management_override'])

        with self.assertRaises(ValidationError):
            validate_customer_credit_limit(self.customer, Decimal("10000.00"), raise_exception=True)


class CustomerViewsTestCase(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_code="CUST-2026-002",
            company_name="MAGA Engineering",
            contact_person="Rohan Fernando",
            phone="+94772223344",
            email="rohan@maga.lk",
            billing_address="Colombo 05",
            credit_limit=Decimal("500000.00"),
            current_outstanding_balance=Decimal("0.00"),
            status=Customer.Status.ACTIVE
        )
        self.site = ProjectSite.objects.create(
            project_code="PRJ-COL-002",
            customer=self.customer,
            project_name="Marine Drive Extension",
            site_address="Bambalapitiya",
            status=ProjectSite.Status.ACTIVE
        )

    def test_unauthenticated_views_redirect_to_login(self):
        # Customer List
        res = self.client.get('/rentals/customers/')
        self.assertEqual(res.status_code, 302)

        # Customer Detail
        res = self.client.get(f'/rentals/customers/{self.customer.customer_code}/')
        self.assertEqual(res.status_code, 302)

        # Customer Create
        res = self.client.get('/rentals/customers/create/')
        self.assertEqual(res.status_code, 302)

        # Site List
        res = self.client.get('/rentals/sites/')
        self.assertEqual(res.status_code, 302)

        # Site Create
        res = self.client.get('/rentals/sites/create/')
        self.assertEqual(res.status_code, 302)


class QuotationContractModelTestCase(TestCase):
    def setUp(self):
        from users.models import User
        from fleet.models import Category, Equipment
        from datetime import date, datetime

        self.user = User.objects.create_user(
            username="ops_officer",
            email="ops@cerms.com",
            password="securepassword123",
            role=User.Role.OPERATIONS_OFFICER
        )

        self.customer = Customer.objects.create(
            customer_code="CUST-2026-003",
            company_name="Sanken Construction",
            contact_person="Nimal Dias",
            phone="+94773334455",
            email="nimal@sanken.lk",
            billing_address="Colombo 02",
            credit_limit=Decimal("2000000.00"),
            status=Customer.Status.ACTIVE
        )

        self.site = ProjectSite.objects.create(
            project_code="PRJ-COL-003",
            customer=self.customer,
            project_name="Cinnamon Life Tower Phase 2",
            site_address="Glenn Street, Colombo 02",
            status=ProjectSite.Status.ACTIVE
        )

        self.category = Category.objects.create(
            name="Excavators",
            code="EXC"
        )

        self.equipment = Equipment.objects.create(
            asset_code="EQ-CAT-320-001",
            equipment_name="CAT 320D Hydraulic Excavator",
            category=self.category,
            brand="Caterpillar",
            model_number="320D",
            serial_number="CAT320D-2026-001",
            manufacture_year=2024,
            purchase_cost=Decimal("35000000.00"),
            purchase_date=date(2024, 1, 15),
            current_hour_meter=Decimal("1250.00"),
            status=Equipment.Status.AVAILABLE
        )

        self.quotation = Quotation.objects.create(
            quotation_no="QT-2026-0001",
            customer=self.customer,
            project_site=self.site,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            rate_applied=Decimal("45000.00"),
            rate_type=Quotation.RateType.DAILY,
            estimated_transport_cost=Decimal("50000.00"),
            security_deposit_required=Decimal("100000.00"),
            discount_percentage=Decimal("5.00"),
            subtotal_amount=Decimal("427500.00"),
            total_tax_amount=Decimal("76950.00"),
            grand_total_amount=Decimal("554450.00"),
            status=Quotation.Status.DRAFT
        )

        self.contract = RentalContract.objects.create(
            contract_no="CNT-2026-0001",
            quotation=self.quotation,
            customer=self.customer,
            project_site=self.site,
            equipment=self.equipment,
            contract_start_date=date(2026, 11, 1),
            contract_end_date=date(2026, 11, 10),
            billing_cycle=RentalContract.BillingCycle.MONTHLY,
            agreed_rate=Decimal("45000.00"),
            deposit_paid=Decimal("100000.00"),
            status=RentalContract.Status.ACTIVE
        )

        self.dispatch_return = DispatchReturn.objects.create(
            transaction_id="TRX-2026-0001",
            contract=self.contract,
            equipment=self.equipment,
            dispatch_datetime=datetime(2026, 11, 1, 8, 30),
            dispatch_hour_meter=Decimal("1250.00"),
            dispatch_fuel_level=Decimal("100.00"),
            dispatch_officer=self.user,
            dispatch_checklist={"cabin": "clean", "hydraulics": "good", "tracks": "intact"}
        )

    def test_quotation_properties(self):
        self.assertEqual(str(self.quotation), "QT-2026-0001 - Sanken Construction (Draft)")
        self.assertEqual(self.quotation.duration_days, 10)
        self.assertEqual(self.quotation.rental_duration_days, 10)
        self.assertEqual(self.quotation.discount_amount, Decimal("21375.00"))  # 5% of 427,500
        self.assertFalse(self.quotation.is_approved)

    def test_quotation_calculation_service(self):
        # 10 days @ 45,000 = 450,000 base
        # 5% discount = 22,500
        # Transport = 50,000
        # VAT 18% on (450,000 - 22,500 + 50,000) = 18% of 477,500 = 85,950
        # Grand Total = (450,000 + 50,000 + 85,950) - 22,500 = 563,450.00
        result = calculate_quotation_totals(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            rate_applied=Decimal("45000.00"),
            estimated_transport_cost=Decimal("50000.00"),
            discount_percentage=Decimal("5.00"),
        )
        self.assertEqual(result['duration_days'], 10)
        self.assertEqual(result['base_tariff'], Decimal("450000.00"))
        self.assertEqual(result['discount_amount'], Decimal("22500.00"))
        self.assertEqual(result['estimated_transport_cost'], Decimal("50000.00"))
        self.assertEqual(result['total_tax_amount'], Decimal("85950.00"))
        self.assertEqual(result['grand_total_amount'], Decimal("563450.00"))
        # Ensure grand_total is NOT equal to discount_amount
        self.assertNotEqual(result['grand_total_amount'], result['discount_amount'])

    def test_quotation_model_save_and_calculate_totals(self):
        # Test Quotation model calculation
        q = Quotation.objects.create(
            quotation_no="QT-2026-9999",
            customer=self.customer,
            project_site=self.site,
            equipment=self.equipment,
            start_date=date(2026, 10, 6),
            end_date=date(2026, 10, 6),  # 1 day
            rate_applied=Decimal("450000.00"),
            rate_type=Quotation.RateType.DAILY,
            estimated_transport_cost=Decimal("25000.00"),
            discount_percentage=Decimal("5.00"),
            total_tax_amount=Decimal("47500.00"),
            grand_total_amount=Decimal("22500.00"),  # buggy input (just the discount)
        )
        # On save, grand_total_amount is corrected: (450,000 + 25,000 + 47,500) - 22,500 = 500,000.00
        self.assertEqual(q.grand_total_amount, Decimal("500000.00"))
        self.assertEqual(q.discount_amount, Decimal("22500.00"))

    def test_quotation_form_clean_calculates_correct_grand_total(self):
        form_data = {
            'quotation_no': 'QT-2026-0002',
            'customer': self.customer.pk,
            'project_site': self.site.pk,
            'equipment': self.equipment.pk,
            'start_date': '2026-11-01',
            'end_date': '2026-11-10',
            'rate_type': Quotation.RateType.DAILY,
            'rate_applied': '45000.00',
            'estimated_transport_cost': '50000.00',
            'security_deposit_required': '100000.00',
            'discount_percentage': '5.00',
            'subtotal_amount': '450000.00',
            'total_tax_amount': '85950.00',
            'grand_total_amount': '22500.00',  # submitted buggy value
            'status': Quotation.Status.DRAFT,
        }
        form = QuotationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        quotation = form.save()
        # Form clean must correct grand_total_amount: (450,000 + 50,000 + 85,950) - 22,500 = 563,450.00
        self.assertEqual(quotation.grand_total_amount, Decimal("563450.00"))

    def test_contract_and_dispatch_properties(self):
        self.assertEqual(str(self.contract), "CNT-2026-0001 - Sanken Construction (EQ-CAT-320-001)")
        self.assertEqual(str(self.dispatch_return), "TRX-2026-0001 - EQ-CAT-320-001 (CNT-2026-0001)")
        self.assertEqual(self.dispatch_return.hours_operated, Decimal("0.00"))

        # Test Return completion
        self.dispatch_return.return_hour_meter = Decimal("1325.50")
        self.dispatch_return.return_fuel_level = Decimal("85.00")
        self.assertEqual(self.dispatch_return.hours_operated, Decimal("75.50"))


class AvailabilityCalendarAndConflictTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='rental_officer_test',
            email='rental_test@cerms.com',
            password='Password123!',
            role=User.Role.RENTAL_OFFICER
        )

        self.category_excavator = Category.objects.create(
            name="Excavators",
            code="EXC",
            description="Heavy Earthmoving Excavators"
        )
        self.category_crane = Category.objects.create(
            name="Cranes",
            code="CRN",
            description="Mobile & Crawler Cranes"
        )

        self.eq_available = Equipment.objects.create(
            asset_code="EQ-CAT-320-001",
            equipment_name="Caterpillar 320D Excavator",
            category=self.category_excavator,
            brand="Caterpillar",
            model_number="320D",
            serial_number="CAT320D-TEST-001",
            manufacture_year=2022,
            purchase_cost=Decimal("45000000.00"),
            purchase_date=date(2022, 1, 15),
            current_hour_meter=Decimal("1250.00"),
            status=Equipment.Status.AVAILABLE
        )

        self.eq_rented = Equipment.objects.create(
            asset_code="EQ-KOM-PC200-001",
            equipment_name="Komatsu PC200-8 Excavator",
            category=self.category_excavator,
            brand="Komatsu",
            model_number="PC200-8",
            serial_number="KOMPC200-TEST-002",
            manufacture_year=2021,
            purchase_cost=Decimal("40000000.00"),
            purchase_date=date(2021, 6, 10),
            current_hour_meter=Decimal("2100.00"),
            status=Equipment.Status.ON_RENT
        )

        self.eq_maint = Equipment.objects.create(
            asset_code="EQ-KOB-CK1000-001",
            equipment_name="Kobelco CK1000 Crane",
            category=self.category_crane,
            brand="Kobelco",
            model_number="CK1000",
            serial_number="KOBCK1000-TEST-003",
            manufacture_year=2020,
            purchase_cost=Decimal("85000000.00"),
            purchase_date=date(2020, 3, 20),
            current_hour_meter=Decimal("3400.00"),
            status=Equipment.Status.MAINTENANCE
        )

        self.customer = Customer.objects.create(
            customer_code="CUST-2026-999",
            company_name="Dimo Engineering Ltd",
            contact_person="Nimal Bandara",
            phone="+94773334455",
            email="nimal@dimo.lk",
            billing_address="Colombo 14",
            credit_limit=Decimal("5000000.00"),
            status=Customer.Status.ACTIVE
        )

        self.site = ProjectSite.objects.create(
            project_code="PRJ-DIMO-001",
            customer=self.customer,
            project_name="Port City Marine Terminal",
            site_address="Colombo Port City",
            status=ProjectSite.Status.ACTIVE
        )

        # Quotation for eq_available in late November
        self.quote_reserved = Quotation.objects.create(
            quotation_no="QT-2026-9999",
            customer=self.customer,
            project_site=self.site,
            equipment=self.eq_available,
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 25),
            rate_applied=Decimal("45000.00"),
            subtotal_amount=Decimal("270000.00"),
            grand_total_amount=Decimal("318600.00"),
            status=Quotation.Status.ACCEPTED
        )

        # Active Contract for eq_rented from Nov 1 to Nov 15
        self.contract_quote = Quotation.objects.create(
            quotation_no="QT-2026-8888",
            customer=self.customer,
            project_site=self.site,
            equipment=self.eq_rented,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 15),
            rate_applied=Decimal("50000.00"),
            subtotal_amount=Decimal("750000.00"),
            grand_total_amount=Decimal("885000.00"),
            status=Quotation.Status.CONVERTED
        )

        self.contract_active = RentalContract.objects.create(
            contract_no="CNT-2026-9999",
            quotation=self.contract_quote,
            customer=self.customer,
            project_site=self.site,
            equipment=self.eq_rented,
            contract_start_date=date(2026, 11, 1),
            contract_end_date=date(2026, 11, 15),
            agreed_rate=Decimal("50000.00"),
            status=RentalContract.Status.ON_RENT
        )

    def test_overlap_detection_query(self):
        from fleet.managers import get_available_equipment

        # During Nov 1 - Nov 10: eq_rented is occupied with CNT-2026-9999, eq_maint is in maintenance
        # eq_available is free
        available_qs = get_available_equipment(
            category_id=self.category_excavator.id,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10)
        )
        self.assertIn(self.eq_available, available_qs)
        self.assertNotIn(self.eq_rented, available_qs)
        self.assertNotIn(self.eq_maint, available_qs)

        # In December 2026: both excavators are unreserved
        dec_available = get_available_equipment(
            category_id=self.category_excavator.id,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 10)
        )
        # eq_rented status is ON_RENT so status='AVAILABLE' excludes it unless transitioned, eq_available is included
        self.assertIn(self.eq_available, dec_available)

    def test_availability_calendar_view(self):
        self.client.force_login(self.user)
        response = self.client.get('/rentals/availability-calendar/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'rentals/calendar.html')
        self.assertIn('categories', response.context)
        self.assertIn('total_equipment', response.context)
        self.assertEqual(response.context['total_equipment'], 3)
        self.assertEqual(response.context['available_count'], 1)
        self.assertEqual(response.context['on_rent_count'], 1)
        self.assertEqual(response.context['maintenance_count'], 1)

    def test_calendar_events_api(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/rentals/calendar-events/?start=2026-10-01&end=2026-12-31')
        self.assertEqual(response.status_code, 200)
        events = response.json()
        self.assertIsInstance(events, list)

        # Should include contract event (Blue), quote reservation (Yellow), and maintenance (Red)
        event_types = [e['extendedProps']['type'] for e in events]
        self.assertIn('ON_RENT', event_types)
        self.assertIn('RESERVED', event_types)
        self.assertIn('MAINTENANCE', event_types)

        contract_event = next(e for e in events if e['extendedProps']['type'] == 'ON_RENT')
        self.assertEqual(contract_event['backgroundColor'], '#0d6efd')

        quote_event = next(e for e in events if e['extendedProps']['type'] == 'RESERVED')
        self.assertEqual(quote_event['backgroundColor'], '#ffc107')

        maint_event = next(e for e in events if e['extendedProps']['type'] == 'MAINTENANCE')
        self.assertEqual(maint_event['backgroundColor'], '#dc3545')

    def test_equipment_availability_check_api(self):
        self.client.force_login(self.user)
        response = self.client.get(
            f'/rentals/api/check-availability/?start_date=2026-11-01&end_date=2026-11-10&category_id={self.category_excavator.id}'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total_available'], 1)
        self.assertEqual(data['equipment'][0]['asset_code'], self.eq_available.asset_code)
        self.assertIn('create_quote_url', data['equipment'][0])


