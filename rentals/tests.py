from datetime import date, datetime
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from users.models import User
from fleet.models import Category, Equipment
from .models import Customer, ProjectSite, Quotation, QuotationItem, RentalContract, RentalContractItem, DispatchReturn
from .services import validate_customer_credit_limit, calculate_quotation_totals, convert_quotation_to_contract
from .forms import QuotationForm, QuotationItemForm, QuotationItemFormSet


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
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
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
            'items-0-start_date': '2026-11-01',
            'items-0-end_date': '2026-11-10',
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




