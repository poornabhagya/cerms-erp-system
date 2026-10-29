from datetime import date, datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.urls import reverse

from users.models import User
from fleet.models import Category, Equipment, RentalRate
from .models import Customer, ProjectSite, Quotation, QuotationItem, RentalContract, RentalContractItem, DispatchReturn
from .services import (
    validate_customer_credit_limit,
    calculate_quotation_totals,
    convert_quotation_to_contract,
    render_quotation_to_pdf,
    render_contract_to_pdf,
    validate_equipment_availability,
)
from .forms import QuotationForm, QuotationItemForm, QuotationItemFormSet, RentalContractForm


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

    def test_customer_code_auto_generation(self):
        # 1. Test generate_customer_code format
        code = Customer.generate_customer_code(year=2026)
        self.assertEqual(code, "CUST-2026-002")

        # 2. Test auto-creation when customer_code is omitted/empty
        new_cust = Customer.objects.create(
            company_name="Tudawe Brothers Ltd",
            contact_person="Ajith Tudawe",
            phone="+94776665544",
            email="ajith@tudawe.lk",
            billing_address="Colombo 08",
            credit_limit=Decimal("1500000.00")
        )
        self.assertEqual(new_cust.customer_code, "CUST-2026-002")

        # 3. Next code should increment to 003
        next_code = Customer.generate_customer_code(year=2026)
        self.assertEqual(next_code, "CUST-2026-003")

    def test_customer_form_code_handling(self):
        from rentals.forms import CustomerForm
        # New form initializes with next customer code
        form = CustomerForm()
        self.assertEqual(form.initial.get('customer_code'), "CUST-2026-002")

        # Submit form with empty customer_code
        post_data = {
            'customer_code': '',
            'company_name': 'Sierra Construction',
            'contact_person': 'Prasanna De Silva',
            'phone': '+94778889900',
            'email': 'prasanna@sierra.lk',
            'billing_address': 'Kaduwela',
            'credit_limit': '3000000.00',
            'current_outstanding_balance': '0.00',
            'status': 'ACTIVE',
        }
        bound_form = CustomerForm(data=post_data)
        self.assertTrue(bound_form.is_valid(), bound_form.errors)
        created_cust = bound_form.save()
        self.assertEqual(created_cust.customer_code, "CUST-2026-002")


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

        self.equipment2 = Equipment.objects.create(
            asset_code="EQ-KOM-PC200-001",
            equipment_name="Komatsu PC200-8 Excavator",
            category=self.category,
            brand="Komatsu",
            model_number="PC200-8",
            serial_number="KOMPC200-2026-001",
            manufacture_year=2024,
            purchase_cost=Decimal("32000000.00"),
            purchase_date=date(2024, 2, 1),
            current_hour_meter=Decimal("950.00"),
            status=Equipment.Status.AVAILABLE
        )

        self.quotation = Quotation.objects.create(
            quotation_no="QT-2026-0001",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            rate_type=Quotation.RateType.DAILY,
            estimated_transport_cost=Decimal("50000.00"),
            security_deposit_required=Decimal("100000.00"),
            discount_percentage=Decimal("5.00"),
            subtotal_amount=Decimal("450000.00"),
            total_tax_amount=Decimal("85950.00"),
            grand_total_amount=Decimal("563450.00"),
            status=Quotation.Status.DRAFT
        )

        self.quotation_item = QuotationItem.objects.create(
            quotation=self.quotation,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            rate_type=Quotation.RateType.DAILY,
            rate_applied=Decimal("45000.00"),
            subtotal_amount=Decimal("450000.00")
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

        self.contract_item = RentalContractItem.objects.create(
            contract=self.contract,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            rate_type=Quotation.RateType.DAILY,
            rate_applied=Decimal("45000.00"),
            subtotal_amount=Decimal("450000.00")
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
        self.assertEqual(self.quotation.discount_amount, Decimal("22500.00"))  # 5% of 450,000
        self.assertEqual(self.quotation.taxable_base_amount, Decimal("477500.00")) # 450,000 - 22,500 + 50,000
        self.assertFalse(self.quotation.is_approved)

    def test_quotation_calculation_service_single_item(self):
        # 10 days @ 45,000 = 450,000 base
        # 5% discount = 22,500
        # Transport = 50,000
        # Taxable Base = 450,000 - 22,500 + 50,000 = 477,500
        # VAT 18% = 85,950
        # Grand Total = 477,500 + 85,950 = 563,450.00
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
        self.assertEqual(result['taxable_base'], Decimal("477500.00"))
        self.assertEqual(result['estimated_transport_cost'], Decimal("50000.00"))
        self.assertEqual(result['total_tax_amount'], Decimal("85950.00"))
        self.assertEqual(result['grand_total_amount'], Decimal("563450.00"))

    def test_multi_item_quotation_calculations(self):
        # Multi-Item Quote:
        # Item 1: 10 days @ 45,000 = 450,000
        # Item 2: 5 days @ 40,000 = 200,000
        # Base Tariff = 650,000
        # Transport = 60,000
        # Discount 10% = 65,000
        # Taxable Base = (650,000 - 65,000) + 60,000 = 645,000
        # VAT 18% = 116,100
        # Grand Total = 645,000 + 116,100 = 761,100.00
        items = [
            {'start_date': date(2026, 11, 1), 'end_date': date(2026, 11, 10), 'rate_applied': Decimal('45000.00'), 'subtotal_amount': Decimal('450000.00')},
            {'start_date': date(2026, 11, 1), 'end_date': date(2026, 11, 5), 'rate_applied': Decimal('40000.00'), 'subtotal_amount': Decimal('200000.00')},
        ]
        result = calculate_quotation_totals(
            items=items,
            estimated_transport_cost=Decimal('60000.00'),
            discount_percentage=Decimal('10.00'),
        )
        self.assertEqual(result['base_tariff'], Decimal('650000.00'))
        self.assertEqual(result['discount_amount'], Decimal('65000.00'))
        self.assertEqual(result['taxable_base'], Decimal('645000.00'))
        self.assertEqual(result['total_tax_amount'], Decimal('116100.00'))
        self.assertEqual(result['grand_total_amount'], Decimal('761100.00'))

    def test_multi_item_quotation_contract_conversion(self):
        # Create quote with 2 items and mark accepted
        quote = Quotation.objects.create(
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 10),
            subtotal_amount=Decimal('650000.00'),
            discount_percentage=Decimal('10.00'),
            estimated_transport_cost=Decimal('60000.00'),
            security_deposit_required=Decimal('150000.00'),
            total_tax_amount=Decimal('116100.00'),
            grand_total_amount=Decimal('761100.00'),
            status=Quotation.Status.ACCEPTED
        )
        QuotationItem.objects.create(
            quotation=quote,
            equipment=self.equipment,
            rate_applied=Decimal('45000.00'),
            subtotal_amount=Decimal('450000.00')
        )
        QuotationItem.objects.create(
            quotation=quote,
            equipment=self.equipment2,
            rate_applied=Decimal('40000.00'),
            subtotal_amount=Decimal('200000.00')
        )

        contract = convert_quotation_to_contract(quote.quotation_no, user=self.user)
        self.assertEqual(contract.customer, self.customer)
        self.assertEqual(contract.items.count(), 2)

        # Verify machinery assets transitioned to RESERVED
        self.equipment.refresh_from_db()
        self.equipment2.refresh_from_db()
        self.assertEqual(self.equipment.status, Equipment.Status.RESERVED)
        self.assertEqual(self.equipment2.status, Equipment.Status.RESERVED)

        # Verify quote marked converted
        quote.refresh_from_db()
        self.assertEqual(quote.status, Quotation.Status.CONVERTED)

    def test_quotation_model_save_and_calculate_totals(self):
        q = Quotation.objects.create(
            quotation_no="QT-2026-9999",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 10, 6),
            end_date=date(2026, 10, 6),  # 1 day
            subtotal_amount=Decimal("450000.00"),
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
            'start_date': '2026-11-01',
            'end_date': '2026-11-10',
            'rate_type': Quotation.RateType.DAILY,
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

    def test_quotation_no_auto_generation(self):
        # 1. Existing quotation in setUp is QT-2026-0001 -> next code should be QT-2026-0002
        next_code = Quotation.generate_quotation_no(year=2026)
        self.assertEqual(next_code, "QT-2026-0002")

        # 2. Test empty year start -> QT-2027-0001
        new_year_code = Quotation.generate_quotation_no(year=2027)
        self.assertEqual(new_year_code, "QT-2027-0001")

        # 3. Create another quotation without quotation_no and verify auto-assignment
        new_quote = Quotation.objects.create(
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 15),
            end_date=date(2026, 11, 20),
            rate_type=Quotation.RateType.DAILY,
        )
        self.assertEqual(new_quote.quotation_no, "QT-2026-0002")

        # 4. Create one with a higher sequence number to test non-contiguous max sequence discovery
        Quotation.objects.create(
            quotation_no="QT-2026-0010",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 5),
            rate_type=Quotation.RateType.DAILY,
        )
        # Next code should be QT-2026-0011
        self.assertEqual(Quotation.generate_quotation_no(year=2026), "QT-2026-0011")

    def test_quotation_form_auto_generation_and_readonly(self):
        # 1. New form initializes with next quotation_no and readonly widget
        form = QuotationForm()
        self.assertTrue(form.fields['quotation_no'].widget.attrs.get('readonly'))
        self.assertIn('bg-light', form.fields['quotation_no'].widget.attrs.get('class', ''))
        self.assertEqual(form.initial.get('quotation_no'), "QT-2026-0002")

        # 2. Form submission without quotation_no should auto-assign next number
        form_data = {
            'customer': self.customer.pk,
            'project_site': self.site.pk,
            'start_date': '2026-11-01',
            'end_date': '2026-11-10',
            'rate_type': Quotation.RateType.DAILY,
            'estimated_transport_cost': '50000.00',
            'security_deposit_required': '100000.00',
            'discount_percentage': '5.00',
            'subtotal_amount': '450000.00',
            'status': Quotation.Status.DRAFT,
        }
        form = QuotationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        saved_quote = form.save()
        self.assertEqual(saved_quote.quotation_no, "QT-2026-0002")

    def test_formset_extra_empty_row_ignored_on_save(self):
        # Test that an extra unselected line item row does not trigger "This field is required" error
        formset_data = {
            'items-TOTAL_FORMS': '2',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '1',
            'items-MAX_NUM_FORMS': '1000',
            # Item 0 (Valid Item)
            'items-0-equipment': str(self.equipment.pk),
            'items-0-start_date': '2026-12-01',
            'items-0-end_date': '2026-12-10',
            'items-0-rate_type': Quotation.RateType.DAILY,
            'items-0-rate_applied': '45000.00',
            'items-0-subtotal_amount': '450000.00',
            # Item 1 (Extra empty unselected row)
            'items-1-equipment': '',
            'items-1-start_date': '',
            'items-1-end_date': '',
            'items-1-rate_type': Quotation.RateType.DAILY,
            'items-1-rate_applied': '',
            'items-1-subtotal_amount': '',
        }
        formset = QuotationItemFormSet(data=formset_data)
        self.assertTrue(formset.is_valid(), formset.errors)
        # Verify only 1 valid form is recognized
        valid_forms = [f for f in formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE') and f.cleaned_data.get('equipment')]
        self.assertEqual(len(valid_forms), 1)

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
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 25),
            subtotal_amount=Decimal("270000.00"),
            grand_total_amount=Decimal("318600.00"),
            status=Quotation.Status.ACCEPTED
        )
        QuotationItem.objects.create(
            quotation=self.quote_reserved,
            equipment=self.eq_available,
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 25),
            rate_applied=Decimal("45000.00"),
            subtotal_amount=Decimal("270000.00")
        )

        # Active Contract for eq_rented from Nov 1 to Nov 15
        self.contract_quote = Quotation.objects.create(
            quotation_no="QT-2026-8888",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 15),
            subtotal_amount=Decimal("750000.00"),
            grand_total_amount=Decimal("885000.00"),
            status=Quotation.Status.CONVERTED
        )
        QuotationItem.objects.create(
            quotation=self.contract_quote,
            equipment=self.eq_rented,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 15),
            rate_applied=Decimal("50000.00"),
            subtotal_amount=Decimal("750000.00")
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
        RentalContractItem.objects.create(
            contract=self.contract_active,
            equipment=self.eq_rented,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 15),
            rate_applied=Decimal("50000.00"),
            subtotal_amount=Decimal("750000.00")
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


class ProjectSiteAutoCodeAndDeletionTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin_tester",
            email="admin_site@cerms.com",
            password="AdminPassword123!",
            role=User.Role.ADMINISTRATOR
        )
        self.rental_officer = User.objects.create_user(
            username="rental_tester",
            email="rental_site@cerms.com",
            password="StaffPassword123!",
            role=User.Role.RENTAL_OFFICER
        )
        self.ops_officer = User.objects.create_user(
            username="ops_tester",
            email="ops_site@cerms.com",
            password="StaffPassword123!",
            role=User.Role.OPERATIONS_OFFICER
        )

        self.customer = Customer.objects.create(
            customer_code="CUST-2026-001",
            company_name="Access Engineering PLC",
            contact_person="Sunil Perera",
            phone="+94771234567",
            email="sunil@accesseng.lk",
            billing_address="Colombo 03",
            credit_limit=Decimal("2000000.00"),
            status=Customer.Status.ACTIVE
        )
        self.customer2 = Customer.objects.create(
            customer_code="CUST-2026-009",
            company_name="Maga Engineering",
            contact_person="Rohan Fernando",
            phone="+94772223344",
            email="rohan@maga.lk",
            billing_address="Colombo 05",
            credit_limit=Decimal("1500000.00"),
            status=Customer.Status.ACTIVE
        )

    def test_project_code_generation_algorithm(self):
        # 1. First site for customer 001
        code_1 = ProjectSite.generate_project_code(customer=self.customer)
        self.assertEqual(code_1, "PRJ-001-01")

        site_1 = ProjectSite.objects.create(
            customer=self.customer,
            project_name="Interchange Section A",
            site_address="Mirigama Site",
            status=ProjectSite.Status.ACTIVE
        )
        self.assertEqual(site_1.project_code, "PRJ-001-01")

        # 2. Second site for customer 001 should increment to 02
        code_2 = ProjectSite.generate_project_code(customer=self.customer)
        self.assertEqual(code_2, "PRJ-001-02")

        # 3. First site for customer 009
        code_cust2 = ProjectSite.generate_project_code(customer=self.customer2)
        self.assertEqual(code_cust2, "PRJ-009-01")

    def test_project_site_status_management(self):
        site = ProjectSite.objects.create(
            customer=self.customer,
            project_name="Marine Drive Ext",
            site_address="Colombo 03",
            status=ProjectSite.Status.ACTIVE
        )
        self.assertEqual(site.status, ProjectSite.Status.ACTIVE)

        # Transition to COMPLETED
        site.status = ProjectSite.Status.COMPLETED
        site.save()
        self.assertEqual(site.status, ProjectSite.Status.COMPLETED)

        # Transition to INACTIVE
        site.status = ProjectSite.Status.INACTIVE
        site.save()
        self.assertEqual(site.status, ProjectSite.Status.INACTIVE)

    def test_project_site_form_and_api(self):
        from rentals.forms import ProjectSiteForm

        # API endpoint for code generation
        self.client.force_login(self.rental_officer)
        response = self.client.get(f'/rentals/api/generate-site-code/?customer={self.customer.customer_code}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['project_code'], "PRJ-001-01")

        # Form saves with auto-generated code
        form_data = {
            'project_code': '',
            'customer': self.customer.customer_code,
            'project_name': 'Kandy Tunnel Project',
            'site_address': 'Kandy Interchange',
            'gps_coordinates': '7.2906,80.6337',
            'site_contact_person': 'Nuwan Perera',
            'site_contact_phone': '+94771112233',
            'status': 'ACTIVE',
        }
        form = ProjectSiteForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        saved_site = form.save()
        self.assertEqual(saved_site.project_code, "PRJ-001-01")

    def test_admin_can_delete_unlinked_project_site(self):
        site = ProjectSite.objects.create(
            customer=self.customer,
            project_name="Temporary Work Depot",
            site_address="Kelaniya",
            status=ProjectSite.Status.INACTIVE
        )
        self.client.force_login(self.admin)
        response = self.client.post(f'/rentals/sites/{site.project_code}/delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ProjectSite.objects.filter(project_code=site.project_code).exists())

    def test_non_admin_cannot_delete_project_site(self):
        site = ProjectSite.objects.create(
            customer=self.customer,
            project_name="Restricted Site Depot",
            site_address="Ja-Ela",
            status=ProjectSite.Status.ACTIVE
        )
        # Rental officer should be 403 Forbidden
        self.client.force_login(self.rental_officer)
        response = self.client.post(f'/rentals/sites/{site.project_code}/delete/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(ProjectSite.objects.filter(project_code=site.project_code).exists())

        # Operations officer should be 403 Forbidden
        self.client.force_login(self.ops_officer)
        response2 = self.client.post(f'/rentals/sites/{site.project_code}/delete/')
        self.assertEqual(response2.status_code, 403)
        self.assertTrue(ProjectSite.objects.filter(project_code=site.project_code).exists())

    def test_delete_blocked_when_linked_to_quotation(self):
        category = Category.objects.create(name='Heavy Haulage', code='HAUL')
        equipment = Equipment.objects.create(
            asset_code='EQ-HAUL-VOL-FH16-001',
            equipment_name='Volvo FH16 Prime Mover',
            category=category,
            brand='Volvo',
            model_number='FH16',
            serial_number='VOL-FH16-101',
            manufacture_year=2023,
            purchase_cost=Decimal('45000000.00'),
            purchase_date=date.today(),
            current_hour_meter=Decimal('120.00'),
            status=Equipment.Status.AVAILABLE
        )
        site = ProjectSite.objects.create(
            customer=self.customer,
            project_name="Central Highway Project",
            site_address="Kurunegala",
            status=ProjectSite.Status.ACTIVE
        )
        quote = Quotation.objects.create(
            quotation_no="QT-2026-5555",
            customer=self.customer,
            project_site=site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 15),
            subtotal_amount=Decimal("900000.00"),
            grand_total_amount=Decimal("1062000.00"),
            status=Quotation.Status.DRAFT
        )
        QuotationItem.objects.create(
            quotation=quote,
            equipment=equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 15),
            rate_applied=Decimal("60000.00"),
            subtotal_amount=Decimal("900000.00")
        )

        self.client.force_login(self.admin)
        response = self.client.post(f'/rentals/sites/{site.project_code}/delete/')
        self.assertEqual(response.status_code, 302)
        # Site must still exist due to protection check
        self.assertTrue(ProjectSite.objects.filter(project_code=site.project_code).exists())


class QuotationDeletionSecurityTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_quote_user',
            email='admin_quote@cerms.com',
            password='Password123!',
            role=User.Role.ADMINISTRATOR
        )
        self.rental_officer = User.objects.create_user(
            username='ro_quote_user',
            email='ro_quote@cerms.com',
            password='Password123!',
            role=User.Role.RENTAL_OFFICER
        )
        self.customer = Customer.objects.create(
            customer_code='CUST-2026-099',
            company_name='Keangnam Enterprises',
            contact_person='Mr. Kim',
            phone='+94778889900',
            email='kim@keangnam.lk',
            billing_address='Colombo 03',
            credit_limit=Decimal('5000000.00'),
            status=Customer.Status.ACTIVE
        )
        self.site = ProjectSite.objects.create(
            project_code='PRJ-099-01',
            customer=self.customer,
            project_name='Port City Complex',
            site_address='Port City, Colombo',
            status=ProjectSite.Status.ACTIVE
        )
        self.category = Category.objects.create(name='Mobile Cranes', code='CRN')
        self.equipment = Equipment.objects.create(
            asset_code='EQ-CRN-KATO-50T-001',
            equipment_name='Kato 50T Rough Terrain Crane',
            category=self.category,
            brand='Kato',
            model_number='KR500',
            serial_number='KATO-KR500-2024',
            manufacture_year=2024,
            purchase_cost=Decimal('65000000.00'),
            purchase_date=date.today(),
            current_hour_meter=Decimal('500.00'),
            status=Equipment.Status.AVAILABLE
        )

    def test_admin_can_delete_unconverted_quotation(self):
        quote = Quotation.objects.create(
            quotation_no='QT-2026-8888',
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 5),
            subtotal_amount=Decimal('400000.00'),
            grand_total_amount=Decimal('472000.00'),
            status=Quotation.Status.DRAFT
        )
        QuotationItem.objects.create(
            quotation=quote,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 5),
            rate_applied=Decimal('80000.00'),
            subtotal_amount=Decimal('400000.00')
        )
        self.client.force_login(self.admin)
        response = self.client.post(f'/rentals/quotations/{quote.quotation_no}/delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Quotation.objects.filter(quotation_no='QT-2026-8888').exists())

    def test_non_admin_cannot_delete_quotation(self):
        quote = Quotation.objects.create(
            quotation_no='QT-2026-8889',
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 5),
            subtotal_amount=Decimal('400000.00'),
            grand_total_amount=Decimal('472000.00'),
            status=Quotation.Status.DRAFT
        )
        QuotationItem.objects.create(
            quotation=quote,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 5),
            rate_applied=Decimal('80000.00'),
            subtotal_amount=Decimal('400000.00')
        )
        self.client.force_login(self.rental_officer)
        response = self.client.post(f'/rentals/quotations/{quote.quotation_no}/delete/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Quotation.objects.filter(quotation_no='QT-2026-8889').exists())

    def test_admin_cannot_delete_converted_quotation(self):
        quote = Quotation.objects.create(
            quotation_no='QT-2026-8890',
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 5),
            subtotal_amount=Decimal('400000.00'),
            grand_total_amount=Decimal('472000.00'),
            status=Quotation.Status.CONVERTED
        )
        QuotationItem.objects.create(
            quotation=quote,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 5),
            rate_applied=Decimal('80000.00'),
            subtotal_amount=Decimal('400000.00')
        )
        contract = RentalContract.objects.create(
            contract_no='CNT-2026-8890',
            quotation=quote,
            customer=self.customer,
            project_site=self.site,
            equipment=self.equipment,
            contract_start_date=date(2026, 11, 1),
            contract_end_date=date(2026, 11, 5),
            billing_cycle=RentalContract.BillingCycle.MONTHLY,
            agreed_rate=Decimal('80000.00'),
            deposit_paid=Decimal('200000.00'),
            status=RentalContract.Status.ACTIVE
        )
        self.client.force_login(self.admin)
        response = self.client.post(f'/rentals/quotations/{quote.quotation_no}/delete/')
        self.assertEqual(response.status_code, 302)
        # Quotation must still exist
        self.assertTrue(Quotation.objects.filter(quotation_no='QT-2026-8890').exists())


from django.test import SimpleTestCase


class DispatchCreateViewTestCase(SimpleTestCase):
    """Unit tests for DispatchCreateView safe equipment handling."""

    def test_dispatch_create_view_with_none_equipment_redirects_and_messages(self):
        from unittest.mock import MagicMock, patch
        from rentals.views import DispatchCreateView
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage

        factory = RequestFactory()
        req = factory.get('/rentals/contracts/CNT-2026-TEST/dispatch/')
        req.user = MagicMock(is_authenticated=True, role='OPERATIONS_OFFICER', is_superuser=False)
        setattr(req, 'session', 'session')
        messages = FallbackStorage(req)
        setattr(req, '_messages', messages)

        mock_contract = MagicMock()
        mock_contract.contract_no = 'CNT-2026-TEST'
        mock_contract.equipment = None

        view = DispatchCreateView()
        with patch('rentals.views.get_object_or_404', return_value=mock_contract):
            response = view.dispatch(req, contract_no='CNT-2026-TEST')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/rentals/contracts/CNT-2026-TEST/')
        msg_texts = [str(m) for m in messages]
        self.assertIn("No equipment assigned to this contract for dispatch.", msg_texts)

    def test_dispatch_create_view_get_initial_safe_when_no_equipment(self):
        from unittest.mock import MagicMock, patch
        from rentals.views import DispatchCreateView

        mock_contract = MagicMock()
        mock_contract.contract_no = 'CNT-2026-TEST'
        mock_contract.equipment = None

        view = DispatchCreateView()
        view.kwargs = {'contract_no': 'CNT-2026-TEST'}
        with patch('rentals.views.get_object_or_404', return_value=mock_contract), \
             patch('rentals.views.DispatchReturn.objects.filter') as mock_dr:
            mock_dr.return_value.count.return_value = 0
            initial = view.get_initial()

        self.assertEqual(initial.get('dispatch_hour_meter'), 0.0)
        self.assertIsNone(initial.get('equipment'))

    def test_dispatch_create_view_get_initial_with_equipment(self):
        from unittest.mock import MagicMock, patch
        from rentals.views import DispatchCreateView

        mock_contract = MagicMock()
        mock_contract.contract_no = 'CNT-2026-TEST'
        mock_contract.equipment = MagicMock(current_hour_meter=Decimal('450.00'))

        view = DispatchCreateView()
        view.kwargs = {'contract_no': 'CNT-2026-TEST'}
        with patch('rentals.views.get_object_or_404', return_value=mock_contract), \
             patch('rentals.views.DispatchReturn.objects.filter') as mock_dr:
            mock_dr.return_value.count.return_value = 0
            initial = view.get_initial()

        self.assertEqual(initial.get('dispatch_hour_meter'), Decimal('450.00'))
        self.assertEqual(initial.get('equipment'), mock_contract.equipment)

    def test_dispatch_create_view_get_context_data_safe_when_no_equipment(self):
        from unittest.mock import MagicMock, patch
        from rentals.views import DispatchCreateView

        mock_contract = MagicMock()
        mock_contract.contract_no = 'CNT-2026-TEST'
        mock_contract.equipment = None

        view = DispatchCreateView()
        view.request = MagicMock()
        view.object = None
        view.kwargs = {'contract_no': 'CNT-2026-TEST'}
        with patch('rentals.views.get_object_or_404', return_value=mock_contract), \
             patch('rentals.views.DispatchReturn.objects.filter') as mock_dr, \
             patch('rentals.forms.DispatchForm'):
            mock_dr.return_value.count.return_value = 0
            context = view.get_context_data()

        self.assertIsNone(context.get('equipment'))
        self.assertEqual(context.get('contract'), mock_contract)


class ReturnFormTestCase(SimpleTestCase):
    """Unit tests for ReturnForm and ReturnCreateView interactive checklist integration."""

    def test_return_form_checklist_widget_is_hidden_input(self):
        from django import forms
        from rentals.forms import ReturnForm

        form = ReturnForm()
        self.assertIsInstance(form.fields['return_checklist'].widget, forms.HiddenInput)
        self.assertEqual(form.fields['return_checklist'].widget.attrs.get('id'), 'id_return_checklist_json')
        self.assertFalse(form.fields['return_checklist'].required)

    def test_return_form_clean_valid_json_checklist(self):
        from rentals.forms import ReturnForm
        data = {
            'return_datetime': '2026-11-10T17:00',
            'return_hour_meter': '1355.5',
            'return_fuel_level': '80',
            'damage_reported': False,
            'damage_notes': '',
            'return_checklist': '{"Cabin & Windshield": {"status": "Pass", "remarks": ""}}',
        }
        form = ReturnForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['return_checklist'], {"Cabin & Windshield": {"status": "Pass", "remarks": ""}})

    def test_return_create_view_get_initial_safe(self):
        from unittest.mock import MagicMock
        from rentals.views import ReturnCreateView

        view = ReturnCreateView()
        view.object = MagicMock()
        view.object.equipment = MagicMock(current_hour_meter=Decimal('1250.00'))

        initial = view.get_initial()
        self.assertEqual(initial['return_hour_meter'], Decimal('1250.00'))
        self.assertEqual(initial['return_fuel_level'], Decimal('100.00'))


class QuotationMaintenanceSoftWarningTestCase(TestCase):
    """
    Unit tests validating soft warning logic for assets in MAINTENANCE or BREAKDOWN
    status during quotation creation and managerial approval.
    """

    def setUp(self):
        self.category = Category.objects.create(
            name="Excavators",
            code="EXC",
            description="Earthmoving equipment"
        )
        self.eq_available = Equipment.objects.create(
            asset_code="EQ-EXC-CAT-001",
            equipment_name="CAT 320D Excavator",
            category=self.category,
            brand="Caterpillar",
            model_number="320D",
            serial_number="SN-CAT-320-9991",
            manufacture_year=2022,
            purchase_cost=Decimal("25000000.00"),
            purchase_date=date(2022, 1, 15),
            current_hour_meter=Decimal("1200.00"),
            status=Equipment.Status.AVAILABLE
        )
        self.eq_maintenance = Equipment.objects.create(
            asset_code="EQ-EXC-KOM-002",
            equipment_name="Komatsu PC200 Excavator",
            category=self.category,
            brand="Komatsu",
            model_number="PC200",
            serial_number="SN-KOM-200-9992",
            manufacture_year=2021,
            purchase_cost=Decimal("22000000.00"),
            purchase_date=date(2021, 5, 20),
            current_hour_meter=Decimal("1850.00"),
            status=Equipment.Status.MAINTENANCE
        )
        self.eq_breakdown = Equipment.objects.create(
            asset_code="EQ-EXC-VOL-003",
            equipment_name="Volvo EC210 Excavator",
            category=self.category,
            brand="Volvo",
            model_number="EC210",
            serial_number="SN-VOL-210-9993",
            manufacture_year=2020,
            purchase_cost=Decimal("21000000.00"),
            purchase_date=date(2020, 8, 10),
            current_hour_meter=Decimal("2400.00"),
            status=Equipment.Status.BREAKDOWN
        )
        self.customer = Customer.objects.create(
            customer_code="CUST-2026-999",
            company_name="Mega Builders PLC",
            contact_person="Nimal Perera",
            phone="+94771112233",
            email="nimal@megabuilders.lk",
            credit_limit=Decimal("5000000.00")
        )
        self.site = ProjectSite.objects.create(
            project_code="PRJ-999-01",
            customer=self.customer,
            project_name="Highway Expansion Project"
        )
        self.manager_user = User.objects.create_user(
            username='mgmt_tester',
            email='mgmt@cerms.lk',
            password='TestPassword123!',
            role=User.Role.MANAGEMENT
        )
        self.rental_officer = User.objects.create_user(
            username='ro_tester',
            email='ro@cerms.lk',
            password='TestPassword123!',
            role=User.Role.RENTAL_OFFICER
        )

    def test_maintenance_assets_not_blocked_in_quotation_item(self):
        """Quotation creation allows equipment in MAINTENANCE or BREAKDOWN status without errors."""
        quote = Quotation.objects.create(
            quotation_no="QT-2026-9001",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 10),
            status=Quotation.Status.DRAFT
        )
        item_maint = QuotationItem.objects.create(
            quotation=quote,
            equipment=self.eq_maintenance,
            rate_applied=Decimal("50000.00"),
            subtotal_amount=Decimal("500000.00")
        )
        item_break = QuotationItem.objects.create(
            quotation=quote,
            equipment=self.eq_breakdown,
            rate_applied=Decimal("45000.00"),
            subtotal_amount=Decimal("450000.00")
        )

        self.assertTrue(item_maint.is_under_maintenance)
        self.assertTrue(item_break.is_under_maintenance)
        self.assertTrue(quote.has_maintenance_items)

    def test_available_asset_not_marked_as_maintenance(self):
        """Available equipment does not flag is_under_maintenance."""
        quote = Quotation.objects.create(
            quotation_no="QT-2026-9002",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 10),
            status=Quotation.Status.DRAFT
        )
        item_avail = QuotationItem.objects.create(
            quotation=quote,
            equipment=self.eq_available,
            rate_applied=Decimal("50000.00"),
            subtotal_amount=Decimal("500000.00")
        )
        self.assertFalse(item_avail.is_under_maintenance)
        self.assertFalse(quote.has_maintenance_items)

    def test_quotation_formset_allows_maintenance_equipment(self):
        """QuotationItemFormSet validates successfully when quoting a machine under maintenance."""
        formset_data = {
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '1',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-equipment': self.eq_maintenance.asset_code,
            'items-0-start_date': '2026-12-01',
            'items-0-end_date': '2026-12-10',
            'items-0-rate_type': Quotation.RateType.DAILY,
            'items-0-rate_applied': '50000.00',
            'items-0-subtotal_amount': '500000.00',
        }
        formset = QuotationItemFormSet(data=formset_data)
        self.assertTrue(formset.is_valid(), formset.errors)

    def test_quotation_create_and_update_views_context_status_map(self):
        """Quotation create and update views provide equipment_status_map in context."""
        from django.test import RequestFactory
        from rentals.views import QuotationCreateView, QuotationUpdateView

        factory = RequestFactory()

        # Create View
        req_create = factory.get('/rentals/quotations/create/')
        req_create.user = self.rental_officer
        view_create = QuotationCreateView()
        view_create.setup(req_create)
        view_create.object = None
        context_create = view_create.get_context_data()
        self.assertIn('equipment_status_map', context_create)
        self.assertTrue(context_create['equipment_status_map'][self.eq_maintenance.asset_code]['is_under_maintenance'])
        self.assertTrue(context_create['equipment_status_map'][self.eq_breakdown.asset_code]['is_under_maintenance'])
        self.assertFalse(context_create['equipment_status_map'][self.eq_available.asset_code]['is_under_maintenance'])

        # Update View
        quote = Quotation.objects.create(
            quotation_no="QT-2026-9003",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 10),
            status=Quotation.Status.DRAFT
        )
        req_update = factory.get(f'/rentals/quotations/{quote.quotation_no}/edit/')
        req_update.user = self.rental_officer
        view_update = QuotationUpdateView()
        view_update.setup(req_update, quotation_no=quote.quotation_no)
        view_update.object = quote
        context_update = view_update.get_context_data()
        self.assertIn('equipment_status_map', context_update)
        self.assertTrue(context_update['equipment_status_map'][self.eq_maintenance.asset_code]['is_under_maintenance'])

    def test_quotation_detail_view_context_has_maintenance_items(self):
        """QuotationDetailView exposes has_maintenance_items boolean in context."""
        from django.test import RequestFactory
        from rentals.views import QuotationDetailView

        factory = RequestFactory()
        quote = Quotation.objects.create(
            quotation_no="QT-2026-9004",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 10),
            status=Quotation.Status.PENDING_INTERNAL_APPROVAL
        )
        QuotationItem.objects.create(
            quotation=quote,
            equipment=self.eq_maintenance,
            rate_applied=Decimal("50000.00"),
            subtotal_amount=Decimal("500000.00")
        )

        req = factory.get(f'/rentals/quotations/{quote.quotation_no}/')
        req.user = self.manager_user
        view = QuotationDetailView()
        view.setup(req, quotation_no=quote.quotation_no)
        view.object = quote
        context = view.get_context_data()
        self.assertTrue(context['has_maintenance_items'])

    def test_managerial_approval_of_quotation_with_maintenance_item(self):
        """Authorizing manager can approve quotation with maintenance items after advisory warning."""
        quote = Quotation.objects.create(
            quotation_no="QT-2026-9005",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 10),
            status=Quotation.Status.PENDING_INTERNAL_APPROVAL
        )
        QuotationItem.objects.create(
            quotation=quote,
            equipment=self.eq_maintenance,
            rate_applied=Decimal("50000.00"),
            subtotal_amount=Decimal("500000.00")
        )
        self.client.force_login(self.manager_user)
        response = self.client.post(
            f'/rentals/quotations/{quote.quotation_no}/transition/',
            {'action': 'approve'}
        )
        self.assertEqual(response.status_code, 302)
        quote.refresh_from_db()
        self.assertEqual(quote.status, Quotation.Status.APPROVED_BY_MANAGEMENT)
        self.assertEqual(quote.approved_by, self.manager_user)


class MultiAssetQuotationToContractTestCase(TestCase):
    """
    Test suite for multi-asset quotation conversion to contract,
    multi-asset display on contract detail page, individual equipment dispatch,
    and partial return lifecycle.
    """

    def setUp(self):
        self.ops_user = User.objects.create_user(
            username="yard_ops",
            email="ops@cerms.lk",
            password="testpassword",
            role=User.Role.OPERATIONS_OFFICER
        )
        self.rental_officer = User.objects.create_user(
            username="rental_rep",
            email="rep@cerms.lk",
            password="testpassword",
            role=User.Role.RENTAL_OFFICER
        )

        self.customer = Customer.objects.create(
            customer_code="CUST-MULTI-01",
            company_name="Mega Builders Ltd",
            contact_person="Ravi Silva",
            phone="+94770001122",
            email="ravi@megabuilders.lk",
            billing_address="Colombo Yard",
            credit_limit=Decimal("5000000.00"),
            status=Customer.Status.ACTIVE
        )

        self.site = ProjectSite.objects.create(
            project_code="PRJ-MULTI-01",
            customer=self.customer,
            project_name="Port City Highway",
            site_address="Colombo Port City",
            status=ProjectSite.Status.ACTIVE
        )

        self.category = Category.objects.create(name="Earthmoving", description="Excavators and Loaders")

        self.eq1 = Equipment.objects.create(
            asset_code="EXC-2026-001",
            equipment_name="CAT 320D Excavator",
            category=self.category,
            brand="Caterpillar",
            model_number="320D",
            serial_number="CAT-SN-001",
            manufacture_year=2024,
            purchase_cost=Decimal("35000000.00"),
            purchase_date=date(2024, 1, 15),
            current_hour_meter=Decimal("120.5"),
            status=Equipment.Status.AVAILABLE
        )

        self.eq2 = Equipment.objects.create(
            asset_code="EXC-2026-002",
            equipment_name="Komatsu PC200 Excavator",
            category=self.category,
            brand="Komatsu",
            model_number="PC200-8",
            serial_number="KOM-SN-002",
            manufacture_year=2024,
            purchase_cost=Decimal("32000000.00"),
            purchase_date=date(2024, 2, 1),
            current_hour_meter=Decimal("340.0"),
            status=Equipment.Status.AVAILABLE
        )

        # Create multi-item quotation
        self.quotation = Quotation.objects.create(
            quotation_no="QT-MULTI-2026-01",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            security_deposit_required=Decimal("100000.00"),
            status=Quotation.Status.ACCEPTED
        )

        QuotationItem.objects.create(
            quotation=self.quotation,
            equipment=self.eq1,
            rate_applied=Decimal("25000.00"),
            subtotal_amount=Decimal("250000.00")
        )

        QuotationItem.objects.create(
            quotation=self.quotation,
            equipment=self.eq2,
            rate_applied=Decimal("30000.00"),
            subtotal_amount=Decimal("300000.00")
        )

    def test_multi_asset_quotation_conversion(self):
        """Converts multi-item quotation into single contract with multiple contract items."""
        contract = convert_quotation_to_contract(self.quotation.quotation_no, user=self.rental_officer)

        self.assertEqual(contract.items.count(), 2)
        self.assertEqual(len(contract.assigned_equipment_list), 2)
        self.assertIn(self.eq1, contract.assigned_equipment_list)
        self.assertIn(self.eq2, contract.assigned_equipment_list)

        # Both equipment assets transitioned to RESERVED
        self.eq1.refresh_from_db()
        self.eq2.refresh_from_db()
        self.assertEqual(self.eq1.status, Equipment.Status.RESERVED)
        self.assertEqual(self.eq2.status, Equipment.Status.RESERVED)

    def test_contract_detail_view_displays_all_assets(self):
        """Contract detail page renders all equipment assets and provides can_dispatch=True."""
        contract = convert_quotation_to_contract(self.quotation.quotation_no, user=self.rental_officer)

        self.client.force_login(self.rental_officer)
        response = self.client.get(f'/rentals/contracts/{contract.contract_no}/')
        self.assertEqual(response.status_code, 200)

        # Context contains contract items and undispatched assets
        self.assertEqual(response.context['contract_items'].count(), 2)
        self.assertEqual(len(response.context['undispatched_equipment']), 2)
        self.assertTrue(response.context['can_dispatch'])

        # HTML content shows both machines
        content = response.content.decode('utf-8')
        self.assertIn("EXC-2026-001", content)
        self.assertIn("EXC-2026-002", content)
        self.assertIn("CAT 320D Excavator", content)
        self.assertIn("Komatsu PC200 Excavator", content)

    def test_sequential_dispatch_and_return_lifecycle(self):
        """Test dispatching first asset, verifying contract remains dispatchable for 2nd asset, and return logic."""
        from django.utils import timezone
        contract = convert_quotation_to_contract(self.quotation.quotation_no, user=self.rental_officer)

        self.client.force_login(self.ops_user)

        # 1. Dispatch first asset (eq1)
        dispatch1_response = self.client.post(
            f'/rentals/contracts/{contract.contract_no}/dispatch/',
            {
                'transaction_id': 'TRX-2026-9001',
                'contract': contract.pk,
                'equipment': self.eq1.pk,
                'dispatch_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'dispatch_hour_meter': '125.0',
                'dispatch_fuel_level': '85.00',
                'dispatch_checklist': '{}'
            }
        )
        self.assertEqual(dispatch1_response.status_code, 302)

        contract.refresh_from_db()
        self.eq1.refresh_from_db()
        self.eq2.refresh_from_db()

        self.assertEqual(self.eq1.status, Equipment.Status.ON_RENT)
        self.assertEqual(self.eq2.status, Equipment.Status.RESERVED)
        self.assertEqual(contract.status, RentalContract.Status.ON_RENT)

        # 2. View contract detail: can_dispatch MUST still be True for remaining asset!
        detail_response = self.client.get(f'/rentals/contracts/{contract.contract_no}/')
        self.assertEqual(detail_response.status_code, 200)
        self.assertTrue(detail_response.context['can_dispatch'])
        self.assertEqual(len(detail_response.context['undispatched_equipment']), 1)
        self.assertEqual(detail_response.context['undispatched_equipment'][0], self.eq2)

        # 3. Dispatch second asset (eq2)
        dispatch2_response = self.client.post(
            f'/rentals/contracts/{contract.contract_no}/dispatch/',
            {
                'transaction_id': 'TRX-2026-9002',
                'contract': contract.pk,
                'equipment': self.eq2.pk,
                'dispatch_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'dispatch_hour_meter': '342.0',
                'dispatch_fuel_level': '90.00',
                'dispatch_checklist': '{}'
            }
        )
        self.assertEqual(dispatch2_response.status_code, 302)

        self.eq2.refresh_from_db()
        self.assertEqual(self.eq2.status, Equipment.Status.ON_RENT)

        # Detail view: all assets dispatched, can_dispatch is False, can_return is True
        detail_response2 = self.client.get(f'/rentals/contracts/{contract.contract_no}/')
        self.assertFalse(detail_response2.context['can_dispatch'])
        self.assertTrue(detail_response2.context['can_return'])
        self.assertEqual(detail_response2.context['active_dispatches'].count(), 2)

        # 4. Return first asset (eq1)
        trx1 = DispatchReturn.objects.filter(contract=contract, equipment=self.eq1).first()
        self.assertIsNotNone(trx1)
        return1_response = self.client.post(
            f'/rentals/returns/{trx1.transaction_id}/',
            {
                'return_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'return_hour_meter': '150.0',
                'return_fuel_level': '80.00',
                'damage_reported': False,
                'damage_notes': '',
                'return_checklist': '{}'
            }
        )
        self.assertEqual(return1_response.status_code, 302)

        contract.refresh_from_db()
        self.eq1.refresh_from_db()
        self.eq2.refresh_from_db()

        self.assertEqual(self.eq1.status, Equipment.Status.AVAILABLE)
        self.assertEqual(self.eq2.status, Equipment.Status.ON_RENT)
        # Contract MUST REMAIN ON_RENT because eq2 is still on site!
        self.assertEqual(contract.status, RentalContract.Status.ON_RENT)

        # 5. Return second asset (eq2)
        trx2 = DispatchReturn.objects.filter(contract=contract, equipment=self.eq2).first()
        self.assertIsNotNone(trx2)
        return2_response = self.client.post(
            f'/rentals/returns/{trx2.transaction_id}/',
            {
                'return_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'return_hour_meter': '365.0',
                'return_fuel_level': '85.00',
                'damage_reported': False,
                'damage_notes': '',
                'return_checklist': '{}'
            }
        )
        self.assertEqual(return2_response.status_code, 302)

        contract.refresh_from_db()
        self.eq2.refresh_from_db()

        self.assertEqual(self.eq2.status, Equipment.Status.AVAILABLE)
        # All equipment returned -> Contract status is RETURNED!
        self.assertEqual(contract.status, RentalContract.Status.RETURNED)


class BifurcatedDamageAndMaintenanceTestCase(TestCase):
    """
    Unit tests for enterprise-grade bifurcated damage logging and decoupled maintenance routing.
    Verifies:
      - Minor damage allows asset to return to AVAILABLE with has_minor_damage flag.
      - Require maintenance grounds asset to MAINTENANCE.
      - Checklist fails act solely as condition logs without forcing MAINTENANCE.
      - Pre-existing damage alert on dispatch form.
      - Dual badges on fleet master and contract detail pages.
    """

    def setUp(self):
        from django.utils import timezone
        self.now = timezone.now()

        self.rental_officer = User.objects.create_user(
            username="rental_officer_dmg",
            email="ro_dmg@cerms.lk",
            password="Password123!",
            role=User.Role.RENTAL_OFFICER
        )
        self.ops_user = User.objects.create_user(
            username="ops_officer_dmg",
            email="ops_dmg@cerms.lk",
            password="Password123!",
            role=User.Role.OPERATIONS_OFFICER
        )
        self.category = Category.objects.create(name="Excavators", code="EXC")

        self.equipment = Equipment.objects.create(
            asset_code="EXC-2026-DMG",
            equipment_name="CAT 320D Excavator",
            category=self.category,
            brand="Caterpillar",
            model_number="320D",
            serial_number="CAT-DMG-001",
            manufacture_year=2024,
            purchase_cost=Decimal("35000000.00"),
            purchase_date=date(2024, 1, 15),
            current_hour_meter=Decimal("100.0"),
            status=Equipment.Status.AVAILABLE
        )

        self.customer = Customer.objects.create(
            customer_code="CUST-2026-DMG",
            company_name="Mega Builders PLC",
            contact_person="Sunil Fernando",
            phone="+94771122334",
            email="sunil@megabuilders.lk",
            billing_address="Colombo 03",
            credit_limit=Decimal("5000000.00"),
            current_outstanding_balance=Decimal("0.00")
        )

        self.site = ProjectSite.objects.create(
            project_code="PRJ-DMG-001",
            customer=self.customer,
            project_name="Metro Tunnel Project",
            site_address="Colombo 01"
        )

        self.quotation = Quotation.objects.create(
            quotation_no="QT-DMG-2026-01",
            customer=self.customer,
            project_site=self.site,
            start_date=date.today(),
            end_date=date.today(),
            security_deposit_required=Decimal("50000.00"),
            status=Quotation.Status.ACCEPTED
        )
        QuotationItem.objects.create(
            quotation=self.quotation,
            equipment=self.equipment,
            rate_applied=Decimal("25000.00"),
            subtotal_amount=Decimal("125000.00")
        )
        self.contract = convert_quotation_to_contract(self.quotation.quotation_no, user=self.rental_officer)

        # Dispatch equipment cleanly first
        from rentals.services import process_equipment_dispatch
        self.dispatch_record = process_equipment_dispatch(
            contract_id=self.contract.contract_no,
            dispatch_data={
                'equipment': self.equipment,
                'dispatch_datetime': self.now,
                'dispatch_hour_meter': Decimal('100.0'),
                'dispatch_fuel_level': Decimal('80.00'),
                'dispatch_checklist': {'Tracks': 'Pass'}
            },
            user=self.ops_user
        )

    def test_return_with_minor_damage_only_stays_available(self):
        """Return with minor damage flag keeps equipment AVAILABLE and sets has_minor_damage=True."""
        from rentals.services import process_equipment_return

        record = process_equipment_return(
            dispatch_return_id=self.dispatch_record.transaction_id,
            return_data={
                'return_datetime': self.now,
                'return_hour_meter': Decimal('120.0'),
                'return_fuel_level': Decimal('75.00'),
                'has_minor_damage': True,
                'requires_maintenance': False,
                'damage_notes': 'Scratched side paint and minor cabin dent',
                'return_checklist': {'Tracks': 'Pass'}
            },
            user=self.ops_user
        )

        self.equipment.refresh_from_db()
        # Machine MUST transition to AVAILABLE (can be rented again!)
        self.assertEqual(self.equipment.status, Equipment.Status.AVAILABLE)
        self.assertTrue(self.equipment.has_minor_damage)
        self.assertEqual(self.equipment.minor_damage_notes, 'Scratched side paint and minor cabin dent')
        self.assertTrue(record.has_minor_damage)
        self.assertFalse(record.requires_maintenance)
        self.assertTrue(record.damage_reported)

    def test_return_with_requires_maintenance_grounds_asset(self):
        """Return with requires_maintenance grounds equipment into MAINTENANCE status."""
        from rentals.services import process_equipment_return

        record = process_equipment_return(
            dispatch_return_id=self.dispatch_record.transaction_id,
            return_data={
                'return_datetime': self.now,
                'return_hour_meter': Decimal('130.0'),
                'return_fuel_level': Decimal('70.00'),
                'has_minor_damage': False,
                'requires_maintenance': True,
                'damage_notes': 'Hydraulic ram blown on site',
                'return_checklist': {'Hydraulics': {'status': 'Fail', 'remarks': 'Ram seal blown'}}
            },
            user=self.ops_user
        )

        self.equipment.refresh_from_db()
        # Machine MUST transition to MAINTENANCE
        self.assertEqual(self.equipment.status, Equipment.Status.MAINTENANCE)
        self.assertTrue(record.requires_maintenance)
        self.assertTrue(record.damage_reported)

    def test_checklist_fail_does_not_automatically_trigger_maintenance(self):
        """Checklist failure acts solely as condition log and does NOT trigger MAINTENANCE."""
        from rentals.services import process_equipment_return

        record = process_equipment_return(
            dispatch_return_id=self.dispatch_record.transaction_id,
            return_data={
                'return_datetime': self.now,
                'return_hour_meter': Decimal('115.0'),
                'return_fuel_level': Decimal('70.00'),
                'has_minor_damage': False,
                'requires_maintenance': False,
                'damage_notes': '',
                'return_checklist': {'Cab Glass': {'status': 'Fail', 'remarks': 'Dusty / wiper streak'}}
            },
            user=self.ops_user
        )

        self.equipment.refresh_from_db()
        # Machine returns to AVAILABLE despite checklist fail
        self.assertEqual(self.equipment.status, Equipment.Status.AVAILABLE)
        self.assertFalse(self.equipment.has_minor_damage)
        self.assertFalse(record.requires_maintenance)

    def test_pre_existing_damage_displayed_on_dispatch_page(self):
        """Dispatch form provides pre-existing damage in telemetry JSON and template alert markup."""
        # Close the active contract from setUp so equipment is free to rent
        self.contract.status = RentalContract.Status.CLOSED
        self.contract.save(update_fields=['status'])

        # Flag equipment with pre-existing minor damage
        self.equipment.status = Equipment.Status.AVAILABLE
        self.equipment.has_minor_damage = True
        self.equipment.minor_damage_notes = "Cracked rear tail-light housing"
        self.equipment.save()

        # Contract for this asset via quotation
        quotation2 = Quotation.objects.create(
            quotation_no="QT-DMG-2026-02",
            customer=self.customer,
            project_site=self.site,
            start_date=date.today(),
            end_date=date.today(),
            security_deposit_required=Decimal("50000.00"),
            status=Quotation.Status.ACCEPTED
        )
        QuotationItem.objects.create(
            quotation=quotation2,
            equipment=self.equipment,
            rate_applied=Decimal("25000.00"),
            subtotal_amount=Decimal("75000.00")
        )
        contract2 = convert_quotation_to_contract(quotation2.quotation_no, user=self.rental_officer)

        self.client.force_login(self.ops_user)
        response = self.client.get(f'/rentals/contracts/{contract2.contract_no}/dispatch/')
        self.assertEqual(response.status_code, 200)

        # Telemetry JSON contains pre-existing damage flag & notes
        telemetry_json = response.context['equipment_telemetry_json']
        self.assertIn('"has_minor_damage": true', telemetry_json)
        self.assertIn('Cracked rear tail-light housing', telemetry_json)

        # Template contains previous damage alert placeholder
        content = response.content.decode('utf-8')
        self.assertIn('id="previousDamageAlert"', content)
        self.assertIn('Unresolved Previous Damages:', content)

    def test_maintenance_resolution_clears_minor_damage(self):
        """Transitioning from MAINTENANCE back to AVAILABLE clears minor damage flags."""
        self.equipment.status = Equipment.Status.MAINTENANCE
        self.equipment.has_minor_damage = True
        self.equipment.minor_damage_notes = "Worn bucket teeth"
        self.equipment.save()

        self.equipment.transition_status(Equipment.Status.AVAILABLE, notes="Workshop overhaul complete")
        self.equipment.refresh_from_db()

        self.assertEqual(self.equipment.status, Equipment.Status.AVAILABLE)
        self.assertFalse(self.equipment.has_minor_damage)
        self.assertEqual(self.equipment.minor_damage_notes, "")

    def test_status_badges_rendered_on_fleet_and_contract(self):
        """Dual badges (e.g. AVAILABLE + Minor Damage) render on fleet list and contract detail."""
        from django.urls import reverse
        self.equipment.status = Equipment.Status.AVAILABLE
        self.equipment.has_minor_damage = True
        self.equipment.minor_damage_notes = "Scratched decal on door"
        self.equipment.save()

        self.client.force_login(self.rental_officer)

        # 1. Fleet list
        fleet_response = self.client.get(reverse('fleet:equipment_list'))
        self.assertEqual(fleet_response.status_code, 200)
        fleet_html = fleet_response.content.decode('utf-8')
        self.assertIn('Available', fleet_html)
        self.assertIn('Minor Damage', fleet_html)

        # 2. Contract detail
        contract_response = self.client.get(f'/rentals/contracts/{self.contract.contract_no}/')
        self.assertEqual(contract_response.status_code, 200)
        contract_html = contract_response.content.decode('utf-8')
        self.assertIn('Minor Damage', contract_html)


class CreditLimitAndStandingEnforcementTests(TestCase):
    """
    Unit and integration tests asserting strict enforcement of customer credit limits
    and account statuses (ACTIVE, BLOCKED, INACTIVE) across forms, services, and views.
    """
    def setUp(self):
        self.rental_officer = User.objects.create_user(
            username='ro_credit_tester',
            email='ro_credit@cerms.com',
            password='Password123!',
            role=User.Role.RENTAL_OFFICER
        )
        self.manager_user = User.objects.create_user(
            username='mgmt_credit_tester',
            email='mgmt_credit@cerms.com',
            password='Password123!',
            role=User.Role.MANAGEMENT
        )

        self.category = Category.objects.create(name="Excavators", code="EXC")
        self.equipment = Equipment.objects.create(
            asset_code="EQ-CAT-320-CRD",
            equipment_name="CAT 320D Excavator",
            category=self.category,
            brand="Caterpillar",
            model_number="320D",
            serial_number="CAT320D-CRD-01",
            manufacture_year=2023,
            purchase_cost=Decimal("25000000.00"),
            purchase_date=date(2023, 1, 1),
            status=Equipment.Status.AVAILABLE
        )

        # Customer with LKR 500,000 credit limit and 0 balance
        self.customer = Customer.objects.create(
            customer_code="CUST-CRD-001",
            company_name="Credit Test Corp",
            contact_person="Ravi Perera",
            phone="+94771234567",
            email="ravi@credittest.lk",
            billing_address="Colombo 03",
            credit_limit=Decimal("500000.00"),
            current_outstanding_balance=Decimal("0.00"),
            status=Customer.Status.ACTIVE
        )

        self.site = ProjectSite.objects.create(
            project_code="PRJ-CRD-01",
            customer=self.customer,
            project_name="Commercial Tower Project",
            site_address="Colombo 02",
            status=ProjectSite.Status.ACTIVE
        )

    def test_quotation_form_blocked_when_credit_limit_exceeded(self):
        """QuotationForm.clean() must raise ValidationError when grand total exceeds available credit."""
        form = QuotationForm(data={
            'quotation_no': 'QT-CRD-001',
            'customer': self.customer.pk,
            'project_site': self.site.pk,
            'start_date': date(2026, 11, 1),
            'end_date': date(2026, 11, 10),
            'rate_type': Quotation.RateType.DAILY,
            'subtotal_amount': '600000.00',  # Exceeds 500,000 limit
            'estimated_transport_cost': '0.00',
            'security_deposit_required': '0.00',
            'discount_percentage': '0.00',
            'total_tax_amount': '108000.00',
            'grand_total_amount': '708000.00',
            'status': Quotation.Status.DRAFT,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('customer', form.errors)
        self.assertTrue(any('Credit limit exceeded' in e for e in form.errors['customer']))

    def test_quotation_form_allowed_within_credit_limit(self):
        """QuotationForm.clean() succeeds when grand total is within available credit."""
        form = QuotationForm(data={
            'quotation_no': 'QT-CRD-002',
            'customer': self.customer.pk,
            'project_site': self.site.pk,
            'start_date': date(2026, 11, 1),
            'end_date': date(2026, 11, 5),
            'rate_type': Quotation.RateType.DAILY,
            'subtotal_amount': '200000.00',
            'estimated_transport_cost': '0.00',
            'security_deposit_required': '0.00',
            'discount_percentage': '0.00',
            'total_tax_amount': '36000.00',
            'grand_total_amount': '236000.00',  # Well within 500,000 limit
            'status': Quotation.Status.DRAFT,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_quotation_form_blocked_for_blocked_or_inactive_customer(self):
        """QuotationForm.clean() rejects customers with BLOCKED or INACTIVE status."""
        self.customer.status = Customer.Status.BLOCKED
        self.customer.save()

        form = QuotationForm(data={
            'quotation_no': 'QT-CRD-003',
            'customer': self.customer.pk,
            'project_site': self.site.pk,
            'start_date': date(2026, 11, 1),
            'end_date': date(2026, 11, 5),
            'rate_type': Quotation.RateType.DAILY,
            'subtotal_amount': '10000.00',
            'estimated_transport_cost': '0.00',
            'security_deposit_required': '0.00',
            'discount_percentage': '0.00',
            'status': Quotation.Status.DRAFT,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('customer', form.errors)
        self.assertTrue(any('Blocked' in e for e in form.errors['customer']))

    def test_quotation_create_view_blocks_credit_limit_exceeded(self):
        """QuotationCreateView POST rejects saving quotation exceeding credit limit."""
        self.client.force_login(self.rental_officer)
        post_data = {
            'quotation_no': 'QT-CRD-004',
            'customer': self.customer.pk,
            'project_site': self.site.pk,
            'start_date': '2026-11-01',
            'end_date': '2026-11-10',
            'rate_type': 'DAILY',
            'subtotal_amount': '600000.00',
            'estimated_transport_cost': '0.00',
            'security_deposit_required': '0.00',
            'discount_percentage': '0.00',
            'total_tax_amount': '108000.00',
            'grand_total_amount': '708000.00',
            'status': 'DRAFT',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-equipment': self.equipment.pk,
            'items-0-start_date': '2026-11-01',
            'items-0-end_date': '2026-11-10',
            'items-0-rate_applied': '60000.00',
            'items-0-rate_type': 'DAILY',
            'items-0-subtotal_amount': '600000.00',
        }
        res = self.client.post('/rentals/quotations/create/', post_data)
        self.assertEqual(res.status_code, 200)  # Form re-rendered with validation error
        self.assertFalse(Quotation.objects.filter(quotation_no='QT-CRD-004').exists())

    def test_convert_quotation_to_contract_blocked_if_customer_blocked(self):
        """convert_quotation_to_contract strictly raises ValidationError if customer is BLOCKED."""
        quote = Quotation.objects.create(
            quotation_no="QT-CRD-BLOCKED-01",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 5),
            subtotal_amount=Decimal("100000.00"),
            grand_total_amount=Decimal("118000.00"),
            status=Quotation.Status.ACCEPTED
        )
        QuotationItem.objects.create(
            quotation=quote,
            equipment=self.equipment,
            rate_applied=Decimal("20000.00"),
            subtotal_amount=Decimal("100000.00")
        )

        # Block customer after quote was accepted
        self.customer.status = Customer.Status.BLOCKED
        self.customer.save()

        with self.assertRaises(ValidationError) as ctx:
            convert_quotation_to_contract(quote.quotation_no, user=self.manager_user)
        self.assertIn("Blocked", str(ctx.exception))
        self.assertFalse(hasattr(quote, 'contract'))

    def test_convert_quotation_to_contract_blocked_if_credit_limit_exceeded(self):
        """convert_quotation_to_contract strictly raises ValidationError if exposure exceeds credit limit."""
        # Customer has 500,000 limit. We add 450,000 existing balance.
        self.customer.current_outstanding_balance = Decimal("450000.00")
        self.customer.save()

        # New quote grand total is 118,000. 450k + 118k = 568k > 500k limit.
        quote = Quotation.objects.create(
            quotation_no="QT-CRD-EXCEED-01",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 5),
            subtotal_amount=Decimal("100000.00"),
            grand_total_amount=Decimal("118000.00"),
            status=Quotation.Status.ACCEPTED
        )
        QuotationItem.objects.create(
            quotation=quote,
            equipment=self.equipment,
            rate_applied=Decimal("20000.00"),
            subtotal_amount=Decimal("100000.00")
        )

        with self.assertRaises(ValidationError) as ctx:
            convert_quotation_to_contract(quote.quotation_no, user=self.manager_user)
        self.assertIn("Credit limit exceeded", str(ctx.exception))
        self.assertFalse(hasattr(quote, 'contract'))

    def test_convert_quotation_to_contract_succeeds_within_credit_limit(self):
        """convert_quotation_to_contract succeeds and creates contract when customer is ACTIVE and within credit limit."""
        self.customer.current_outstanding_balance = Decimal("100000.00")
        self.customer.save()

        quote = Quotation.objects.create(
            quotation_no="QT-CRD-OK-01",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 5),
            subtotal_amount=Decimal("100000.00"),
            grand_total_amount=Decimal("118000.00"),  # 100k + 118k = 218k <= 500k
            status=Quotation.Status.ACCEPTED
        )
        QuotationItem.objects.create(
            quotation=quote,
            equipment=self.equipment,
            rate_applied=Decimal("20000.00"),
            subtotal_amount=Decimal("100000.00")
        )

        contract = convert_quotation_to_contract(quote.quotation_no, user=self.manager_user)
        self.assertIsNotNone(contract)
        self.assertEqual(contract.customer, self.customer)
        self.assertEqual(contract.status, RentalContract.Status.ACTIVE)
        quote.refresh_from_db()
        self.assertEqual(quote.status, Quotation.Status.CONVERTED)


class QuotationAndContractPDFTestCase(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            code="EXC",
            name="Heavy Excavator",
            description="Hydraulic crawler excavators",
        )
        self.equipment = Equipment.objects.create(
            asset_code="EQ-CAT-320-001",
            equipment_name="Caterpillar 320D Hydraulic Excavator",
            category=self.category,
            brand="Caterpillar",
            model_number="320D",
            serial_number="CAT320D-2026-9901",
            manufacture_year=2023,
            purchase_cost=Decimal("35000000.00"),
            purchase_date=date(2023, 1, 1),
            status=Equipment.Status.AVAILABLE,
            current_hour_meter=Decimal("1250.50"),
        )
        self.customer = Customer.objects.create(
            customer_code="CUST-PDF-001",
            company_name="Access Engineering PLC",
            contact_person="Sunil Perera",
            phone="+94771234567",
            email="sunil@accesseng.lk",
            billing_address="No. 120, Station Road, Colombo 03",
            vat_tax_number="VAT-123456789-7000",
            credit_limit=Decimal("5000000.00"),
            current_outstanding_balance=Decimal("0.00"),
            status=Customer.Status.ACTIVE,
        )
        self.site = ProjectSite.objects.create(
            project_code="PRJ-PDF-001",
            customer=self.customer,
            project_name="Central Expressway Section III",
            site_address="Mirigama Interchange Site, Mirigama",
            site_contact_person="Kamal Silva",
            site_contact_phone="+94779876543",
            status=ProjectSite.Status.ACTIVE,
        )
        self.rental_officer = User.objects.create_user(
            username="pdf_rental_officer",
            email="ro_pdf@cerms.lk",
            password="testpassword2026",
            role=User.Role.RENTAL_OFFICER,
        )
        self.accountant = User.objects.create_user(
            username="pdf_accountant",
            email="acc_pdf@cerms.lk",
            password="testpassword2026",
            role=User.Role.ACCOUNTANT,
        )
        self.management = User.objects.create_user(
            username="pdf_management",
            email="mgmt_pdf@cerms.lk",
            password="testpassword2026",
            role=User.Role.MANAGEMENT,
        )
        self.unauthorized_user = User.objects.create_user(
            username="pdf_unauth",
            email="unauth_pdf@cerms.lk",
            password="testpassword2026",
            role=User.Role.STOREKEEPER,
        )

        self.quotation = Quotation.objects.create(
            quotation_no="QT-2026-PDF-01",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            rate_type=Quotation.RateType.DAILY,
            estimated_transport_cost=Decimal("35000.00"),
            security_deposit_required=Decimal("150000.00"),
            discount_percentage=Decimal("5.00"),
            subtotal_amount=Decimal("250000.00"),
            total_tax_amount=Decimal("49050.00"),
            grand_total_amount=Decimal("321550.00"),
            status=Quotation.Status.APPROVED_BY_MANAGEMENT,
            approved_by=self.management,
        )
        self.quotation_item = QuotationItem.objects.create(
            quotation=self.quotation,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            rate_type=Quotation.RateType.DAILY,
            rate_applied=Decimal("25000.00"),
            subtotal_amount=Decimal("250000.00"),
        )

        self.contract = RentalContract.objects.create(
            contract_no="CNT-2026-PDF-01",
            quotation=self.quotation,
            customer=self.customer,
            project_site=self.site,
            equipment=self.equipment,
            contract_start_date=date(2026, 11, 1),
            contract_end_date=date(2026, 11, 10),
            billing_cycle=RentalContract.BillingCycle.MONTHLY,
            agreed_rate=Decimal("25000.00"),
            deposit_paid=Decimal("150000.00"),
            status=RentalContract.Status.ACTIVE,
        )
        self.contract_item = RentalContractItem.objects.create(
            contract=self.contract,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            rate_applied=Decimal("25000.00"),
            rate_type=Quotation.RateType.DAILY,
            subtotal_amount=Decimal("250000.00"),
        )

    def test_render_quotation_to_pdf_by_id_and_instance(self):
        """Verify render_quotation_to_pdf renders valid bytes with both ID string and instance."""
        pdf_bytes_by_str = render_quotation_to_pdf(self.quotation.quotation_no)
        self.assertIsInstance(pdf_bytes_by_str, bytes)
        self.assertTrue(len(pdf_bytes_by_str) > 0)

        pdf_bytes_by_obj = render_quotation_to_pdf(self.quotation)
        self.assertIsInstance(pdf_bytes_by_obj, bytes)
        self.assertTrue(len(pdf_bytes_by_obj) > 0)

        content_str = pdf_bytes_by_str.decode('utf-8', errors='ignore')
        self.assertIn("CERMS ERP SYSTEM", content_str)
        self.assertIn("COMMERCIAL QUOTATION", content_str)
        self.assertIn(self.quotation.quotation_no, content_str)
        self.assertIn(self.customer.company_name, content_str)
        self.assertIn(self.equipment.asset_code, content_str)
        self.assertIn("150000.00", content_str)
        self.assertIn("35000.00", content_str)

    def test_render_contract_to_pdf_by_id_and_instance(self):
        """Verify render_contract_to_pdf renders valid bytes with both ID string and instance."""
        pdf_bytes_by_str = render_contract_to_pdf(self.contract.contract_no)
        self.assertIsInstance(pdf_bytes_by_str, bytes)
        self.assertTrue(len(pdf_bytes_by_str) > 0)

        pdf_bytes_by_obj = render_contract_to_pdf(self.contract)
        self.assertIsInstance(pdf_bytes_by_obj, bytes)
        self.assertTrue(len(pdf_bytes_by_obj) > 0)

        content_str = pdf_bytes_by_str.decode('utf-8', errors='ignore')
        self.assertIn("CERMS ERP SYSTEM", content_str)
        self.assertIn("RENTAL CONTRACT AGREEMENT", content_str)
        self.assertIn(self.contract.contract_no, content_str)
        self.assertIn(self.customer.company_name, content_str)
        self.assertIn(self.equipment.serial_number, content_str)
        self.assertIn("OPERATING HOURS & OVERTIME HOUR-METER RULES", content_str)
        self.assertIn("BREAKDOWN & MAINTENANCE LIABILITY CLAUSES", content_str)
        self.assertIn("For the Lessor", content_str)
        self.assertIn("For the Lessee", content_str)

    def test_quotation_pdf_download_view_inline_and_attachment(self):
        """Verify QuotationPDFDownloadView handles inline stream and ?download=1 attachment."""
        self.client.force_login(self.rental_officer)

        url_inline = reverse('rentals:quotation_pdf', kwargs={'quotation_no': self.quotation.quotation_no})
        resp_inline = self.client.get(url_inline)
        self.assertEqual(resp_inline.status_code, 200)
        self.assertEqual(resp_inline['Content-Type'], 'application/pdf')
        self.assertIn('inline', resp_inline['Content-Disposition'])
        self.assertIn(f'Quotation-{self.quotation.quotation_no}.pdf', resp_inline['Content-Disposition'])

        resp_download = self.client.get(url_inline + '?download=1')
        self.assertEqual(resp_download.status_code, 200)
        self.assertEqual(resp_download['Content-Type'], 'application/pdf')
        self.assertIn('attachment', resp_download['Content-Disposition'])

    def test_contract_pdf_download_view_inline_and_attachment(self):
        """Verify ContractPDFDownloadView handles inline stream and ?download=1 attachment."""
        self.client.force_login(self.management)

        url_inline = reverse('rentals:contract_pdf', kwargs={'contract_no': self.contract.contract_no})
        resp_inline = self.client.get(url_inline)
        self.assertEqual(resp_inline.status_code, 200)
        self.assertEqual(resp_inline['Content-Type'], 'application/pdf')
        self.assertIn('inline', resp_inline['Content-Disposition'])
        self.assertIn(f'Contract-{self.contract.contract_no}.pdf', resp_inline['Content-Disposition'])

        resp_download = self.client.get(url_inline + '?download=1')
        self.assertEqual(resp_download.status_code, 200)
        self.assertEqual(resp_download['Content-Type'], 'application/pdf')
        self.assertIn('attachment', resp_download['Content-Disposition'])

    def test_rbac_access_controls_for_pdf_downloads(self):
        """Verify unauthorized users are blocked from downloading Quotation and Contract PDFs."""
        q_url = reverse('rentals:quotation_pdf', kwargs={'quotation_no': self.quotation.quotation_no})
        c_url = reverse('rentals:contract_pdf', kwargs={'contract_no': self.contract.contract_no})

        # Unauthenticated access -> 302 redirect to login
        self.client.logout()
        resp_q_anon = self.client.get(q_url)
        self.assertEqual(resp_q_anon.status_code, 302)
        resp_c_anon = self.client.get(c_url)
        self.assertEqual(resp_c_anon.status_code, 302)

        # Unauthorized role (CUSTOMER) -> 403 or redirect
        self.client.force_login(self.unauthorized_user)
        resp_q_unauth = self.client.get(q_url)
        self.assertIn(resp_q_unauth.status_code, [302, 403])
        resp_c_unauth = self.client.get(c_url)
        self.assertIn(resp_c_unauth.status_code, [302, 403])

        # Authorized roles can access
        for user in [self.rental_officer, self.accountant, self.management]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(q_url).status_code, 200)
            self.assertEqual(self.client.get(c_url).status_code, 200)


class DoubleBookingPreventionAndConflictTestCase(TestCase):
    """
    Exhaustive test suite for double-booking prevention, multi-asset contract
    conflict detection, reserved quotation conflict detection, manager queryset filtering,
    form & formset validation, and contract conversion blocking.
    """

    def setUp(self):
        self.rental_officer = User.objects.create_user(
            username='ro_conflict_test',
            email='ro_conflict@cerms.lk',
            password='TestPassword123!',
            role=User.Role.RENTAL_OFFICER
        )
        self.management = User.objects.create_user(
            username='mgmt_conflict_test',
            email='mgmt_conflict@cerms.lk',
            password='TestPassword123!',
            role=User.Role.MANAGEMENT
        )

        self.category = Category.objects.create(
            name="Excavators",
            code="EXC",
            description="Heavy Earthmoving Excavators"
        )

        # eq_primary: Primary equipment for a contract
        self.eq_primary = Equipment.objects.create(
            asset_code="EQ-PRI-001",
            equipment_name="CAT 330D Excavator",
            category=self.category,
            brand="Caterpillar",
            model_number="330D",
            serial_number="CAT330-001",
            manufacture_year=2023,
            purchase_cost=Decimal("45000000.00"),
            purchase_date=date(2023, 1, 1),
            current_hour_meter=Decimal("500.00"),
            status=Equipment.Status.AVAILABLE
        )

        # eq_multi: Second equipment attached via RentalContractItem
        self.eq_multi = Equipment.objects.create(
            asset_code="EQ-MLT-002",
            equipment_name="CAT 320D Excavator",
            category=self.category,
            brand="Caterpillar",
            model_number="320D",
            serial_number="CAT320-002",
            manufacture_year=2023,
            purchase_cost=Decimal("35000000.00"),
            purchase_date=date(2023, 1, 1),
            current_hour_meter=Decimal("650.00"),
            status=Equipment.Status.AVAILABLE
        )

        # eq_reserved: Equipment reserved under an approved quotation
        self.eq_reserved = Equipment.objects.create(
            asset_code="EQ-RES-003",
            equipment_name="Komatsu PC200 Excavator",
            category=self.category,
            brand="Komatsu",
            model_number="PC200-8",
            serial_number="KOM200-003",
            manufacture_year=2023,
            purchase_cost=Decimal("30000000.00"),
            purchase_date=date(2023, 1, 1),
            current_hour_meter=Decimal("800.00"),
            status=Equipment.Status.AVAILABLE
        )

        # Customer & Site
        self.customer = Customer.objects.create(
            customer_code="CUST-CONF-001",
            company_name="Maga Engineering Ltd",
            contact_person="Rohan Fernando",
            phone="+94771112233",
            email="rohan@maga.lk",
            billing_address="Colombo 02",
            credit_limit=Decimal("10000000.00"),
            status=Customer.Status.ACTIVE
        )

        self.site = ProjectSite.objects.create(
            project_code="PRJ-CONF-001",
            customer=self.customer,
            project_name="Central Expressway Section II",
            site_address="Mirigama",
            status=ProjectSite.Status.ACTIVE
        )

        # 1. Existing Active Contract spanning 2026-11-01 to 2026-11-15
        # Primary asset: eq_primary. Multi-asset item: eq_multi (2026-11-01 to 2026-11-15)
        self.quote_contract = Quotation.objects.create(
            quotation_no="QT-CONF-CONTRACT",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 15),
            subtotal_amount=Decimal("1500000.00"),
            grand_total_amount=Decimal("1770000.00"),
            status=Quotation.Status.CONVERTED
        )
        self.contract_multi = RentalContract.objects.create(
            contract_no="CNT-CONF-0001",
            quotation=self.quote_contract,
            customer=self.customer,
            project_site=self.site,
            equipment=self.eq_primary,
            contract_start_date=date(2026, 11, 1),
            contract_end_date=date(2026, 11, 15),
            agreed_rate=Decimal("50000.00"),
            status=RentalContract.Status.ACTIVE
        )
        RentalContractItem.objects.create(
            contract=self.contract_multi,
            equipment=self.eq_multi,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 15),
            rate_applied=Decimal("45000.00"),
            subtotal_amount=Decimal("675000.00")
        )

        # 2. Existing Approved Quotation (unconverted) spanning 2026-11-10 to 2026-11-20
        # Asset: eq_reserved
        self.quote_reserved = Quotation.objects.create(
            quotation_no="QT-CONF-RESERVED",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 20),
            subtotal_amount=Decimal("440000.00"),
            grand_total_amount=Decimal("519200.00"),
            status=Quotation.Status.APPROVED_BY_MANAGEMENT
        )
        QuotationItem.objects.create(
            quotation=self.quote_reserved,
            equipment=self.eq_reserved,
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 20),
            rate_applied=Decimal("40000.00"),
            subtotal_amount=Decimal("440000.00")
        )

    def test_multi_asset_contract_item_conflict_detection(self):
        """Verify Equipment.is_available_for_dates detects multi-asset contract item overlaps."""
        # Overlapping period (Nov 5 - Nov 12) -> False
        self.assertFalse(
            self.eq_multi.is_available_for_dates(date(2026, 11, 5), date(2026, 11, 12))
        )
        # Exact boundary overlap (Nov 1 - Nov 1) -> False
        self.assertFalse(
            self.eq_multi.is_available_for_dates(date(2026, 11, 1), date(2026, 11, 1))
        )
        # Non-overlapping future period (Nov 16 - Nov 25) -> True
        self.assertTrue(
            self.eq_multi.is_available_for_dates(date(2026, 11, 16), date(2026, 11, 25))
        )
        # Non-overlapping prior period (Oct 20 - Oct 31) -> True
        self.assertTrue(
            self.eq_multi.is_available_for_dates(date(2026, 10, 20), date(2026, 10, 31))
        )
        # Exclude contract itself -> True
        self.assertTrue(
            self.eq_multi.is_available_for_dates(
                date(2026, 11, 5), date(2026, 11, 12),
                exclude_contract_id=self.contract_multi.pk
            )
        )

    def test_quotation_item_reservation_conflict_detection(self):
        """Verify Equipment.is_available_for_dates detects reserved unconverted quotation overlaps."""
        # Overlapping period (Nov 12 - Nov 18) -> False
        self.assertFalse(
            self.eq_reserved.is_available_for_dates(date(2026, 11, 12), date(2026, 11, 18))
        )
        # Non-overlapping period (Nov 21 - Nov 30) -> True
        self.assertTrue(
            self.eq_reserved.is_available_for_dates(date(2026, 11, 21), date(2026, 11, 30))
        )
        # Exclude quotation itself -> True
        self.assertTrue(
            self.eq_reserved.is_available_for_dates(
                date(2026, 11, 12), date(2026, 11, 18),
                exclude_quotation_id=self.quote_reserved.pk
            )
        )

        # Status: ACCEPTED also reserves equipment
        self.quote_reserved.status = Quotation.Status.ACCEPTED
        self.quote_reserved.save(update_fields=['status'])
        self.assertFalse(
            self.eq_reserved.is_available_for_dates(date(2026, 11, 12), date(2026, 11, 18))
        )

        # Status: DRAFT does NOT reserve equipment
        self.quote_reserved.status = Quotation.Status.DRAFT
        self.quote_reserved.save(update_fields=['status'])
        self.assertTrue(
            self.eq_reserved.is_available_for_dates(date(2026, 11, 12), date(2026, 11, 18))
        )

        # Status: REJECTED does NOT reserve equipment
        self.quote_reserved.status = Quotation.Status.REJECTED
        self.quote_reserved.save(update_fields=['status'])
        self.assertTrue(
            self.eq_reserved.is_available_for_dates(date(2026, 11, 12), date(2026, 11, 18))
        )

    def test_get_available_equipment_manager_filtering(self):
        """Verify get_available_equipment excludes multi-asset contract items and reserved quotations."""
        from fleet.managers import get_available_equipment

        # Nov 5 to Nov 12:
        # eq_primary is in contract_multi (direct)
        # eq_multi is in contract_multi (RentalContractItem)
        # eq_reserved is in quote_reserved (QuotationItem, APPROVED_BY_MANAGEMENT)
        available = get_available_equipment(
            category_id=self.category.id,
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 12)
        )
        self.assertNotIn(self.eq_primary, available)
        self.assertNotIn(self.eq_multi, available)
        self.assertNotIn(self.eq_reserved, available)

        # Dec 1 to Dec 10: all are available
        available_dec = get_available_equipment(
            category_id=self.category.id,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 10)
        )
        self.assertIn(self.eq_primary, available_dec)
        self.assertIn(self.eq_multi, available_dec)
        self.assertIn(self.eq_reserved, available_dec)

        # Excluding contract allows eq_multi and eq_primary
        available_ex_contract = get_available_equipment(
            category_id=self.category.id,
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 12),
            exclude_contract_id=self.contract_multi.pk
        )
        self.assertIn(self.eq_primary, available_ex_contract)
        self.assertIn(self.eq_multi, available_ex_contract)
        self.assertNotIn(self.eq_reserved, available_ex_contract)

        # Excluding quotation allows eq_reserved
        available_ex_quote = get_available_equipment(
            category_id=self.category.id,
            start_date=date(2026, 11, 16),
            end_date=date(2026, 11, 18),
            exclude_quotation_id=self.quote_reserved.pk
        )
        self.assertIn(self.eq_reserved, available_ex_quote)

    def test_quotation_item_form_rejects_conflicting_equipment(self):
        """Verify QuotationItemForm.clean raises ValidationError on equipment double-booking."""
        # Attempt to book eq_multi during its active contract period
        form_data = {
            'equipment': self.eq_multi.asset_code,
            'start_date': '2026-11-05',
            'end_date': '2026-11-10',
            'rate_type': Quotation.RateType.DAILY,
            'rate_applied': '45000.00',
            'subtotal_amount': '270000.00',
        }
        form = QuotationItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('equipment', form.errors)
        self.assertIn('already booked or reserved', form.errors['equipment'][0])

        # Attempt to book eq_reserved during its reserved quotation period
        form_data_res = {
            'equipment': self.eq_reserved.asset_code,
            'start_date': '2026-11-12',
            'end_date': '2026-11-15',
            'rate_type': Quotation.RateType.DAILY,
            'rate_applied': '40000.00',
            'subtotal_amount': '160000.00',
        }
        form_res = QuotationItemForm(data=form_data_res)
        self.assertFalse(form_res.is_valid())
        self.assertIn('equipment', form_res.errors)
        self.assertIn('already booked or reserved', form_res.errors['equipment'][0])

    def test_quotation_formset_rejects_intra_formset_duplicate_overlap(self):
        """Verify QuotationItemFormSet prevents duplicate booking of same machine on overlapping dates."""
        formset_data = {
            'items-TOTAL_FORMS': '2',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '1',
            'items-MAX_NUM_FORMS': '1000',
            # Item 0: eq_multi from Dec 1 to Dec 10
            'items-0-equipment': self.eq_multi.asset_code,
            'items-0-start_date': '2026-12-01',
            'items-0-end_date': '2026-12-10',
            'items-0-rate_type': Quotation.RateType.DAILY,
            'items-0-rate_applied': '45000.00',
            'items-0-subtotal_amount': '450000.00',
            # Item 1: same eq_multi from Dec 5 to Dec 15 (overlapping with Item 0)
            'items-1-equipment': self.eq_multi.asset_code,
            'items-1-start_date': '2026-12-05',
            'items-1-end_date': '2026-12-15',
            'items-1-rate_type': Quotation.RateType.DAILY,
            'items-1-rate_applied': '45000.00',
            'items-1-subtotal_amount': '495000.00',
        }
        formset = QuotationItemFormSet(data=formset_data)
        self.assertFalse(formset.is_valid())
        # The second form should contain the overlap error
        form_errors = formset.forms[1].errors
        self.assertIn('equipment', form_errors)
        self.assertIn('multiple times for overlapping date ranges', form_errors['equipment'][0])

    def test_rental_contract_form_rejects_conflicting_equipment(self):
        """Verify RentalContractForm.clean raises ValidationError if equipment is occupied."""
        form_data = {
            'contract_no': 'CNT-CONF-9999',
            'quotation': self.quote_contract.pk,
            'customer': self.customer.pk,
            'project_site': self.site.pk,
            'equipment': self.eq_multi.asset_code,
            'contract_start_date': '2026-11-05',
            'contract_end_date': '2026-11-10',
            'billing_cycle': 'MONTHLY',
            'agreed_rate': '45000.00',
            'deposit_paid': '0.00',
            'status': RentalContract.Status.ACTIVE,
        }
        form = RentalContractForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('equipment', form.errors)
        self.assertIn('already booked or reserved', form.errors['equipment'][0])

    def test_convert_quotation_to_contract_blocks_double_booked_equipment(self):
        """Verify convert_quotation_to_contract raises ValidationError if equipment has conflict."""
        # Create an accepted quotation for eq_multi overlapping with contract_multi
        q_conflict = Quotation.objects.create(
            quotation_no="QT-CONF-DOUBLEBOOK",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 10),
            subtotal_amount=Decimal("270000.00"),
            grand_total_amount=Decimal("318600.00"),
            status=Quotation.Status.ACCEPTED
        )
        QuotationItem.objects.create(
            quotation=q_conflict,
            equipment=self.eq_multi,
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 10),
            rate_applied=Decimal("45000.00"),
            subtotal_amount=Decimal("270000.00")
        )

        with self.assertRaises(ValidationError) as ctx:
            convert_quotation_to_contract(q_conflict.quotation_no, user=self.rental_officer)

        self.assertIn("already booked or reserved", str(ctx.exception))

    def test_quotation_status_transition_blocks_approval_and_acceptance_if_conflict(self):
        """Verify QuotationStatusTransitionView blocks management approval and customer acceptance on double booking."""
        self.client.force_login(self.management)

        # Create draft quotation with eq_multi on dates overlapping contract_multi
        q_draft = Quotation.objects.create(
            quotation_no="QT-CONF-TRANSITION",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 10),
            subtotal_amount=Decimal("270000.00"),
            grand_total_amount=Decimal("318600.00"),
            status=Quotation.Status.DRAFT
        )
        QuotationItem.objects.create(
            quotation=q_draft,
            equipment=self.eq_multi,
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 10),
            rate_applied=Decimal("45000.00"),
            subtotal_amount=Decimal("270000.00")
        )

        transition_url = reverse('rentals:quotation_transition', kwargs={'quotation_no': q_draft.quotation_no})

        # Try to approve -> blocked
        resp_approve = self.client.post(transition_url, {'action': 'approve'}, follow=True)
        q_draft.refresh_from_db()
        self.assertEqual(q_draft.status, Quotation.Status.DRAFT)
        messages_approve = [m.message for m in resp_approve.context['messages']]
        self.assertTrue(any('already booked or reserved' in m for m in messages_approve))

        # Try to mark accepted -> blocked
        resp_accept = self.client.post(transition_url, {'action': 'mark_accepted'}, follow=True)
        q_draft.refresh_from_db()
        self.assertEqual(q_draft.status, Quotation.Status.DRAFT)
        messages_accept = [m.message for m in resp_accept.context['messages']]
        self.assertTrue(any('already booked or reserved' in m for m in messages_accept))


class SeedDummyDataCommandTests(TestCase):
    """Automated test suite for the seed_dummy_data management command."""

    def test_production_safety_check_blocks_execution_without_force(self):
        """Verify command raises CommandError when DEBUG is False and --force is omitted."""
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from django.test import override_settings

        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError) as ctx:
                call_command('seed_dummy_data')
            self.assertIn("CRITICAL", str(ctx.exception))

    def test_seed_dummy_data_populates_required_entities(self):
        """Verify command generates 10 customers, 50 equipment assets, and 20 rental contracts."""
        from django.core.management import call_command
        from rentals.models import Customer, ProjectSite, Quotation, RentalContract, DispatchReturn
        from fleet.models import Equipment, RentalRate
        from finance.models import Invoice, Payment, SecurityDeposit

        call_command('seed_dummy_data', force=True)

        # 1. Customers and Project Sites
        dummy_customers = Customer.objects.filter(customer_code__startswith='CUST-DUMMY-')
        self.assertEqual(dummy_customers.count(), 10)
        self.assertTrue(ProjectSite.objects.filter(project_code__startswith='PRJ-DUMMY-').count() >= 10)

        # 2. Equipment Assets & Rate Cards
        dummy_equipment = Equipment.objects.filter(asset_code__startswith='EQ-DUMMY-')
        self.assertEqual(dummy_equipment.count(), 50)
        for eq in dummy_equipment:
            self.assertTrue(
                RentalRate.objects.filter(equipment=eq, is_active=True).exists(),
                f"Equipment {eq.asset_code} has no active rate card!"
            )
        # Check minor damage flags
        self.assertTrue(dummy_equipment.filter(has_minor_damage=True).exists())

        # 3. Rental Contracts & Lifecycle Distribution
        dummy_contracts = RentalContract.objects.filter(contract_no__startswith='CNT-DUMMY-')
        self.assertEqual(dummy_contracts.count(), 20)

        closed_cnt = dummy_contracts.filter(status=RentalContract.Status.CLOSED).count()
        on_rent_cnt = dummy_contracts.filter(status=RentalContract.Status.ON_RENT).count()
        dispatched_cnt = dummy_contracts.filter(status=RentalContract.Status.DISPATCHED).count()
        active_cnt = dummy_contracts.filter(status=RentalContract.Status.ACTIVE).count()

        self.assertEqual(closed_cnt, 5)
        self.assertEqual(on_rent_cnt, 8)
        self.assertEqual(dispatched_cnt, 3)
        self.assertEqual(active_cnt, 4)

        # 4. Associated Financial & Logistics Documents
        self.assertEqual(Invoice.objects.filter(invoice_no__startswith='INV-DUMMY-').count(), 5)
        self.assertEqual(Payment.objects.filter(payment_id__startswith='PAY-DUMMY-').count(), 5)
        self.assertEqual(SecurityDeposit.objects.filter(deposit_id__startswith='DEP-DUMMY-').count(), 20)
        self.assertEqual(DispatchReturn.objects.filter(transaction_id__startswith='TRX-DUMMY-').count(), 16)

        # 5. Test --clear flag idempotency
        call_command('seed_dummy_data', clear=True, force=True)
        self.assertEqual(Customer.objects.filter(customer_code__startswith='CUST-DUMMY-').count(), 10)
        self.assertEqual(Equipment.objects.filter(asset_code__startswith='EQ-DUMMY-').count(), 50)
        self.assertEqual(RentalContract.objects.filter(contract_no__startswith='CNT-DUMMY-').count(), 20)

        # 6. Verify created_by audit field population on seeded entities
        self.assertEqual(Customer.objects.filter(customer_code__startswith='CUST-DUMMY-', created_by__isnull=True).count(), 0)
        self.assertEqual(Equipment.objects.filter(asset_code__startswith='EQ-DUMMY-', created_by__isnull=True).count(), 0)
        self.assertEqual(RentalContract.objects.filter(contract_no__startswith='CNT-DUMMY-', created_by__isnull=True).count(), 0)
        self.assertEqual(Invoice.objects.filter(invoice_no__startswith='INV-DUMMY-', created_by__isnull=True).count(), 0)
        self.assertEqual(DispatchReturn.objects.filter(transaction_id__startswith='TRX-DUMMY-', created_by__isnull=True).count(), 0)


class AutomatedReturnToInvoiceTriggerTestCase(TestCase):
    """
    Test suite for the Automated Return-to-Invoice Trigger.
    Verifies that when equipment is returned from rent, final charges
    (rental tariff, overtime hours, damages, security deposit offset)
    are calculated automatically and the Tax Invoice is created without
    manual finance module intervention.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='auto_inv_admin',
            email='autoinv_admin@test.com',
            password='password123',
            role=User.Role.ADMINISTRATOR
        )
        self.officer = User.objects.create_user(
            username='auto_inv_officer',
            email='autoinv_officer@test.com',
            password='password123',
            role=User.Role.OPERATIONS_OFFICER
        )
        self.workshop = User.objects.create_user(
            username='auto_inv_workshop',
            email='autoinv_workshop@test.com',
            password='password123',
            role=User.Role.WORKSHOP_MANAGER
        )

        self.customer = Customer.objects.create(
            customer_code='CUST-AUTO-INV-001',
            company_name='Auto Invoice Test Corp',
            contact_person='Test Contact',
            phone='+94 11 2345678',
            email='autoinv@test.com',
            billing_address='100 Test St, Colombo',
            credit_limit=Decimal('5000000.00'),
            current_outstanding_balance=Decimal('0.00'),
            status=Customer.Status.ACTIVE
        )

        self.site = ProjectSite.objects.create(
            project_code='PRJ-AUTO-INV-01',
            customer=self.customer,
            project_name='Auto Invoice Site',
            site_address='Test Site Location',
            status=ProjectSite.Status.ACTIVE
        )

        self.category = Category.objects.create(name='Heavy Excavators', code='HEXC')

        self.equipment = Equipment.objects.create(
            asset_code='EQ-AUTO-INV-001',
            equipment_name='Auto Inv Excavator 320D',
            category=self.category,
            brand='Caterpillar',
            model_number='320D',
            serial_number='VIN-AUTO-INV-001',
            manufacture_year=2022,
            purchase_cost=Decimal('25000000.00'),
            purchase_date=date(2022, 1, 1),
            current_hour_meter=Decimal('1000.00'),
            status=Equipment.Status.ON_RENT
        )

        self.rate_card = RentalRate.objects.create(
            equipment=self.equipment,
            daily_rate=Decimal('40000.00'),
            weekly_rate=Decimal('240000.00'),
            monthly_rate=Decimal('880000.00'),
            hourly_rate=Decimal('5000.00'),
            overtime_hourly_rate=Decimal('6250.00'),
            minimum_rental_hours=8,
            effective_from=date(2026, 1, 1),
            is_active=True
        )

        # 5-day rental (start to end inclusive = 5 days): standard allowance = 5 * 8 = 40 hours
        self.start_date = timezone.now().date() - timedelta(days=4)
        self.end_date = timezone.now().date()

        self.quotation = Quotation.objects.create(
            quotation_no='QT-AUTO-INV-001',
            customer=self.customer,
            project_site=self.site,
            start_date=self.start_date,
            end_date=self.end_date,
            rate_type=Quotation.RateType.DAILY,
            estimated_transport_cost=Decimal('30000.00'),
            security_deposit_required=Decimal('100000.00'),
            subtotal_amount=Decimal('200000.00'),
            total_tax_amount=Decimal('41400.00'),
            grand_total_amount=Decimal('271400.00'),
            status=Quotation.Status.CONVERTED
        )

        self.contract = RentalContract.objects.create(
            contract_no='CNT-AUTO-INV-001',
            quotation=self.quotation,
            customer=self.customer,
            project_site=self.site,
            equipment=self.equipment,
            contract_start_date=self.start_date,
            contract_end_date=self.end_date,
            agreed_rate=Decimal('40000.00'),
            deposit_paid=Decimal('100000.00'),
            status=RentalContract.Status.ON_RENT
        )

        self.contract_item = RentalContractItem.objects.create(
            contract=self.contract,
            equipment=self.equipment,
            start_date=self.start_date,
            end_date=self.end_date,
            rate_applied=Decimal('40000.00'),
            rate_type=Quotation.RateType.DAILY,
            subtotal_amount=Decimal('200000.00')
        )

        # Dispatch log: dispatched at meter 1000.00
        tz = timezone.get_current_timezone()
        disp_dt = timezone.make_aware(
            datetime.combine(self.start_date, datetime.min.time().replace(hour=8, minute=0)),
            tz
        )
        self.dispatch = DispatchReturn.objects.create(
            transaction_id='TRX-AUTO-INV-001',
            contract=self.contract,
            equipment=self.equipment,
            dispatch_datetime=disp_dt,
            dispatch_hour_meter=Decimal('1000.00'),
            dispatch_fuel_level=Decimal('100.00'),
            dispatch_officer=self.officer,
            dispatch_checklist={'engine': 'Good', 'tires': 'Good'}
        )

    def test_process_equipment_return_triggers_automated_invoice(self):
        """
        Verify that returning equipment via process_equipment_return automatically:
        1. Calculates excess hours and overtime charge.
        2. Applies damage charges.
        3. Offsets security deposit held in escrow.
        4. Calculates statutory VAT (18%).
        5. Creates the Tax Invoice record with PDF.
        6. Updates Customer outstanding balance.
        7. Transitions RentalContract status to CLOSED.
        """
        from rentals.services import process_equipment_return
        from finance.models import Invoice

        # Standard hours: 5 days * 8 hrs = 40 hrs.
        # Returned with meter 1050.00 -> 50 hours operated -> 10 excess hours!
        ret_data = {
            'return_datetime': timezone.now(),
            'return_hour_meter': Decimal('1050.00'),
            'return_fuel_level': Decimal('90.00'),
            'has_minor_damage': True,
            'requires_maintenance': False,
            'damage_reported': True,
            'damage_notes': 'Slight scratch on side bumper.',
            'damage_charges': Decimal('15000.00'),
            'return_checklist': {'hydraulics': 'Pass', 'cabin': 'Pass'}
        }

        record = process_equipment_return(self.dispatch.transaction_id, ret_data, user=self.workshop)

        self.assertIsNotNone(record.return_datetime)
        self.assertEqual(record.hours_operated, Decimal('50.00'))
        self.assertEqual(record.excess_hours_calculated, Decimal('10.00'))

        # Verify automated invoice generation
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, RentalContract.Status.CLOSED)

        invoices = self.contract.invoices.all()
        self.assertEqual(invoices.count(), 1)
        invoice = invoices.first()

        self.assertEqual(invoice.contract, self.contract)
        self.assertEqual(invoice.customer, self.customer)
        self.assertEqual(invoice.rental_subtotal, Decimal('200000.00'))
        self.assertEqual(invoice.transport_charges, Decimal('30000.00'))

        # Overtime charge: 10 hrs * Rs. 6,250 = Rs. 62,500.00
        self.assertEqual(invoice.excess_hours_charge, Decimal('62500.00'))
        self.assertEqual(invoice.damage_charges, Decimal('15000.00'))

        # Taxable base: 200,000 + 30,000 + 62,500 + 15,000 = 307,500.00
        # VAT 18%: 307,500 * 0.18 = 55,350.00
        # Gross total: 307,500 + 55,350 = 362,850.00
        # Deposit offset: 100,000.00
        # Net payable: 362,850 - 100,000 = 262,850.00
        self.assertEqual(invoice.deposit_deducted, Decimal('100000.00'))
        self.assertEqual(invoice.tax_amount, Decimal('55350.00'))
        self.assertEqual(invoice.net_total_payable, Decimal('262850.00'))
        self.assertEqual(invoice.status, Invoice.Status.UNPAID)

        # Customer balance updated
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.current_outstanding_balance, Decimal('262850.00'))

    def test_multi_asset_return_triggers_invoice_only_when_all_returned(self):
        """
        In a multi-asset contract, returning the first machine must leave the contract ON_RENT
        without generating an invoice. When the last machine is returned, the final invoice
        must trigger automatically and aggregate excess hours from all equipment.
        """
        from rentals.services import process_equipment_return

        # Add second equipment to this contract
        eq2 = Equipment.objects.create(
            asset_code='EQ-AUTO-INV-002',
            equipment_name='Auto Inv Generator 100kVA',
            category=self.category,
            brand='Cummins',
            model_number='100KVA',
            serial_number='VIN-AUTO-INV-002',
            manufacture_year=2023,
            purchase_cost=Decimal('8000000.00'),
            purchase_date=date(2023, 1, 1),
            current_hour_meter=Decimal('500.00'),
            status=Equipment.Status.ON_RENT
        )
        RentalRate.objects.create(
            equipment=eq2,
            daily_rate=Decimal('20000.00'),
            is_active=True
        )
        RentalContractItem.objects.create(
            contract=self.contract,
            equipment=eq2,
            start_date=self.start_date,
            end_date=self.end_date,
            rate_applied=Decimal('20000.00'),
            rate_type=Quotation.RateType.DAILY,
            subtotal_amount=Decimal('100000.00')
        )

        tz = timezone.get_current_timezone()
        disp_dt = timezone.make_aware(
            datetime.combine(self.start_date, datetime.min.time().replace(hour=9, minute=0)),
            tz
        )
        dispatch2 = DispatchReturn.objects.create(
            transaction_id='TRX-AUTO-INV-002',
            contract=self.contract,
            equipment=eq2,
            dispatch_datetime=disp_dt,
            dispatch_hour_meter=Decimal('500.00'),
            dispatch_fuel_level=Decimal('100.00'),
            dispatch_officer=self.officer
        )

        # 1. Return first machine (Excavator)
        ret1 = {
            'return_datetime': timezone.now(),
            'return_hour_meter': Decimal('1045.00'),  # 5 excess hours
            'return_fuel_level': Decimal('95.00'),
            'damage_charges': Decimal('0.00'),
            'return_checklist': {}
        }
        process_equipment_return(self.dispatch.transaction_id, ret1, user=self.workshop)

        self.contract.refresh_from_db()
        # Machine 2 is still out -> Contract remains ON_RENT, no invoice yet
        self.assertEqual(self.contract.status, RentalContract.Status.ON_RENT)
        self.assertEqual(self.contract.invoices.count(), 0)

        # 2. Return second machine (Generator)
        ret2 = {
            'return_datetime': timezone.now(),
            'return_hour_meter': Decimal('548.00'),  # 8 excess hours
            'return_fuel_level': Decimal('90.00'),
            'damage_charges': Decimal('5000.00'),
            'return_checklist': {}
        }
        process_equipment_return(dispatch2.transaction_id, ret2, user=self.workshop)

        self.contract.refresh_from_db()
        # All equipment returned -> Contract CLOSED and Invoice generated!
        self.assertEqual(self.contract.status, RentalContract.Status.CLOSED)
        self.assertEqual(self.contract.invoices.count(), 1)

        inv = self.contract.invoices.first()
        self.assertEqual(inv.damage_charges, Decimal('5000.00'))
        # Total excess hours across both: 5 (eq1) + 8 (eq2) = 13 hours
        self.assertTrue(inv.excess_hours_charge > Decimal('0.00'))

    def test_return_create_view_integration(self):
        """
        Verify that submitting ReturnCreateView via HTTP POST:
        - Successfully redirects to contract_detail.
        - Emits success message with invoice confirmation.
        - Transitions contract to CLOSED.
        - Creates the commercial Tax Invoice.
        """
        self.client.force_login(self.workshop)
        url = reverse('rentals:return_create', kwargs={'transaction_id': self.dispatch.transaction_id})

        post_data = {
            'return_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'return_hour_meter': '1040.0',
            'return_fuel_level': '95.00',
            'has_minor_damage': '',
            'requires_maintenance': '',
            'damage_notes': '',
            'damage_charges': '0.00',
            'damage_reported': '',
            'return_checklist': '{"engine":"pass"}',
        }

        resp = self.client.post(url, post_data, follow=True)
        self.assertRedirects(resp, reverse('rentals:contract_detail', kwargs={'contract_no': self.contract.contract_no}))

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, RentalContract.Status.CLOSED)
        self.assertEqual(self.contract.invoices.count(), 1)

        messages = [m.message for m in resp.context['messages']]
        self.assertTrue(any('automatically generated' in m for m in messages))

    def test_post_save_signal_triggers_invoice_on_direct_save(self):
        """
        Verify that saving DispatchReturn directly with return_datetime triggers
        the auto_trigger_return_to_invoice signal.
        """
        self.dispatch.return_datetime = timezone.now()
        self.dispatch.return_hour_meter = Decimal('1040.00')
        self.dispatch.return_fuel_level = Decimal('100.00')
        self.dispatch.return_officer = self.workshop
        self.dispatch.save()

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, RentalContract.Status.CLOSED)
        self.assertEqual(self.contract.invoices.count(), 1)










