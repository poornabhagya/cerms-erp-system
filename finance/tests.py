from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from users.models import User
from fleet.models import Category, Equipment
from rentals.models import Customer, ProjectSite, Quotation, QuotationItem, RentalContract, RentalContractItem, DispatchReturn
from finance.models import Invoice, Payment, SecurityDeposit
from finance.services import (
    generate_final_rental_invoice,
    record_invoice_payment,
    process_deposit_refund,
    render_invoice_to_pdf
)


class FinanceModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="accountant_user",
            email="accountant@cerms.lk",
            password="securepassword123",
            role=User.Role.ACCOUNTANT
        )

        self.customer = Customer.objects.create(
            customer_code="CUST-2026-FIN",
            company_name="Access Infrastructure Ltd",
            contact_person="Ravi Wickramasinghe",
            phone="+94771122334",
            email="ravi@access.lk",
            billing_address="No. 45, Baseline Road, Colombo 09",
            credit_limit=Decimal("5000000.00"),
            current_outstanding_balance=Decimal("0.00"),
            status=Customer.Status.ACTIVE
        )

        self.site = ProjectSite.objects.create(
            project_code="PRJ-FIN-001",
            customer=self.customer,
            project_name="Port City Marine Drive",
            site_address="Colombo Port City",
            status=ProjectSite.Status.ACTIVE
        )

        self.category = Category.objects.create(
            name="Excavators",
            code="EXC-FIN"
        )

        self.equipment = Equipment.objects.create(
            asset_code="EQ-CAT-320-FIN",
            equipment_name="CAT 320D Excavator",
            category=self.category,
            brand="Caterpillar",
            model_number="320D",
            serial_number="CAT320D-FIN-001",
            manufacture_year=2024,
            purchase_cost=Decimal("35000000.00"),
            purchase_date=date(2024, 1, 15),
            current_hour_meter=Decimal("1250.00"),
            status=Equipment.Status.AVAILABLE
        )

        self.quotation = Quotation.objects.create(
            quotation_no="QT-2026-FIN-001",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            rate_type=Quotation.RateType.MONTHLY,
            estimated_transport_cost=Decimal("50000.00"),
            security_deposit_required=Decimal("200000.00"),
            subtotal_amount=Decimal("450000.00"),
            total_tax_amount=Decimal("81000.00"),
            grand_total_amount=Decimal("581000.00"),
            status=Quotation.Status.ACCEPTED
        )
        QuotationItem.objects.create(
            quotation=self.quotation,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            rate_applied=Decimal("450000.00"),
            rate_type=Quotation.RateType.MONTHLY,
            subtotal_amount=Decimal("450000.00")
        )

        self.contract = RentalContract.objects.create(
            contract_no="CNT-2026-FIN-001",
            quotation=self.quotation,
            customer=self.customer,
            project_site=self.site,
            equipment=self.equipment,
            contract_start_date=date(2026, 11, 1),
            contract_end_date=date(2026, 11, 30),
            billing_cycle=RentalContract.BillingCycle.MONTHLY,
            agreed_rate=Decimal("450000.00"),
            deposit_paid=Decimal("200000.00"),
            status=RentalContract.Status.ACTIVE
        )
        RentalContractItem.objects.create(
            contract=self.contract,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            rate_applied=Decimal("450000.00"),
            subtotal_amount=Decimal("450000.00")
        )

    def test_invoice_creation_and_properties(self):
        invoice = Invoice.objects.create(
            invoice_no="INV-2026-0001",
            contract=self.contract,
            customer=self.customer,
            invoice_date=date(2026, 11, 30),
            due_date=date(2026, 12, 30),
            billing_period_start=date(2026, 11, 1),
            billing_period_end=date(2026, 11, 30),
            rental_subtotal=Decimal("450000.00"),
            excess_hours_charge=Decimal("25000.00"),
            damage_charges=Decimal("15000.00"),
            transport_charges=Decimal("50000.00"),
            tax_amount=Decimal("97200.00"),
            deposit_deducted=Decimal("100000.00"),
            net_total_payable=Decimal("537200.00"),
            paid_amount=Decimal("0.00"),
            status=Invoice.Status.UNPAID
        )

        self.assertEqual(str(invoice), f"INV-2026-0001 - Access Infrastructure Ltd (LKR 537,200.00) [Unpaid]")
        self.assertEqual(invoice.balance_due, Decimal("537200.00"))
        self.assertFalse(invoice.is_overdue)
        self.assertEqual(invoice.payment_progress_pct, 0.0)

        # Test partial payment update
        invoice.paid_amount = Decimal("200000.00")
        invoice.status = Invoice.Status.PARTIALLY_PAID
        invoice.save()

        self.assertEqual(invoice.balance_due, Decimal("337200.00"))
        self.assertAlmostEqual(invoice.payment_progress_pct, (200000.00 / 537200.00) * 100, places=2)

    def test_payment_creation_and_properties(self):
        invoice = Invoice.objects.create(
            invoice_no="INV-2026-0002",
            contract=self.contract,
            customer=self.customer,
            invoice_date=date(2026, 11, 30),
            due_date=date(2026, 12, 30),
            billing_period_start=date(2026, 11, 1),
            billing_period_end=date(2026, 11, 30),
            rental_subtotal=Decimal("450000.00"),
            net_total_payable=Decimal("450000.00"),
            status=Invoice.Status.UNPAID
        )

        payment = Payment.objects.create(
            payment_id="PAY-2026-0001",
            invoice=invoice,
            customer=self.customer,
            amount=Decimal("450000.00"),
            payment_date=date(2026, 12, 5),
            payment_type=Payment.PaymentType.RENTAL_PAYMENT,
            payment_method=Payment.PaymentMethod.BANK_TRANSFER,
            reference_number="TXN-HNB-987654321",
            recorded_by=self.user,
            notes="Settled via HNB corporate online transfer"
        )

        self.assertEqual(str(payment), f"PAY-2026-0001 - Access Infrastructure Ltd (LKR 450,000.00) [Rental Invoice Payment]")
        self.assertEqual(payment.customer, self.customer)
        self.assertEqual(payment.invoice, invoice)

    def test_security_deposit_creation_and_properties(self):
        deposit = SecurityDeposit.objects.create(
            deposit_id="DEP-2026-0001",
            contract=self.contract,
            customer=self.customer,
            deposit_amount=Decimal("200000.00"),
            received_date=date(2026, 11, 1),
            deducted_amount=Decimal("50000.00"),
            refunded_amount=Decimal("100000.00"),
            status=SecurityDeposit.Status.DEDUCTED
        )

        self.assertEqual(str(deposit), f"DEP-2026-0001 - CNT-2026-FIN-001 (LKR 200,000.00) [Partially / Fully Deducted]")
        self.assertEqual(deposit.remaining_held_amount, Decimal("50000.00"))


class FinanceServicesAndViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.accountant = User.objects.create_user(
            username="test_accountant",
            email="acc@cerms.lk",
            password="securepassword123",
            role=User.Role.ACCOUNTANT
        )

        self.customer = Customer.objects.create(
            customer_code="CUST-2026-SRV",
            company_name="MAGA Engineering PLC",
            contact_person="Anura Jayawardena",
            phone="+94775566778",
            email="anura@maga.lk",
            billing_address="No. 200, Nawala Road, Narahenpita",
            credit_limit=Decimal("10000000.00"),
            current_outstanding_balance=Decimal("0.00"),
            status=Customer.Status.ACTIVE
        )

        self.site = ProjectSite.objects.create(
            project_code="PRJ-SRV-001",
            customer=self.customer,
            project_name="Central Expressway Link",
            site_address="Kadawatha Interchange",
            status=ProjectSite.Status.ACTIVE
        )

        self.category = Category.objects.create(
            name="Excavators",
            code="EXC-SRV"
        )

        self.equipment = Equipment.objects.create(
            asset_code="EQ-CAT-320-SRV",
            equipment_name="CAT 320D Excavator",
            category=self.category,
            brand="Caterpillar",
            model_number="320D",
            serial_number="CAT320D-SRV-001",
            manufacture_year=2024,
            purchase_cost=Decimal("35000000.00"),
            purchase_date=date(2024, 1, 15),
            current_hour_meter=Decimal("1250.00"),
            status=Equipment.Status.AVAILABLE
        )

        self.quotation = Quotation.objects.create(
            quotation_no="QT-2026-SRV-001",
            customer=self.customer,
            project_site=self.site,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            rate_type=Quotation.RateType.DAILY,
            estimated_transport_cost=Decimal("30000.00"),
            security_deposit_required=Decimal("100000.00"),
            subtotal_amount=Decimal("450000.00"),
            total_tax_amount=Decimal("86400.00"),
            grand_total_amount=Decimal("566400.00"),
            status=Quotation.Status.ACCEPTED
        )
        QuotationItem.objects.create(
            quotation=self.quotation,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            rate_applied=Decimal("45000.00"),
            rate_type=Quotation.RateType.DAILY,
            subtotal_amount=Decimal("450000.00")
        )

        self.contract = RentalContract.objects.create(
            contract_no="CNT-2026-SRV-001",
            quotation=self.quotation,
            customer=self.customer,
            project_site=self.site,
            equipment=self.equipment,
            contract_start_date=date(2026, 11, 1),
            contract_end_date=date(2026, 11, 10),
            billing_cycle=RentalContract.BillingCycle.MONTHLY,
            agreed_rate=Decimal("45000.00"),
            deposit_paid=Decimal("100000.00"),
            status=RentalContract.Status.RETURNED
        )
        RentalContractItem.objects.create(
            contract=self.contract,
            equipment=self.equipment,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 10),
            rate_applied=Decimal("45000.00"),
            subtotal_amount=Decimal("450000.00")
        )

        self.dispatch = DispatchReturn.objects.create(
            transaction_id="TRX-2026-SRV-001",
            contract=self.contract,
            equipment=self.equipment,
            dispatch_datetime=timezone.now(),
            dispatch_hour_meter=Decimal("1250.00"),
            dispatch_fuel_level=Decimal("100.00"),
            return_hour_meter=Decimal("1350.00"),
            return_fuel_level=Decimal("100.00"),
            excess_hours_calculated=Decimal("20.00"),
            dispatch_officer=self.accountant
        )

    def test_generate_final_rental_invoice_service(self):
        # Generate final invoice
        invoice = generate_final_rental_invoice(
            contract_id=self.contract.contract_no,
            user=self.accountant,
            due_date=date(2026, 12, 10),
            excess_hours_rate=Decimal("5000.00"),  # 20 hrs * 5000 = 100,000
            damage_charges=Decimal("20000.00"),
            apply_deposit=True,
            tax_rate=Decimal("0.18")
        )

        # Base: 450,000 | Transport: 30,000 | Excess: 100,000 | Damage: 20,000
        # Taxable subtotal = 600,000 | VAT 18% = 108,000 | Gross = 708,000
        # Deposit deducted = 100,000 | Net Payable = 608,000
        self.assertEqual(invoice.rental_subtotal, Decimal("450000.00"))
        self.assertEqual(invoice.transport_charges, Decimal("30000.00"))
        self.assertEqual(invoice.excess_hours_charge, Decimal("100000.00"))
        self.assertEqual(invoice.damage_charges, Decimal("20000.00"))
        self.assertEqual(invoice.tax_amount, Decimal("108000.00"))
        self.assertEqual(invoice.deposit_deducted, Decimal("100000.00"))
        self.assertEqual(invoice.net_total_payable, Decimal("608000.00"))
        self.assertEqual(invoice.status, Invoice.Status.UNPAID)

        # Check Customer exposure balance updated
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.current_outstanding_balance, Decimal("608000.00"))

        # Check Security deposit status
        sec_deposit = SecurityDeposit.objects.get(contract=self.contract)
        self.assertEqual(sec_deposit.deducted_amount, Decimal("100000.00"))

    def test_record_invoice_payment_service(self):
        invoice = generate_final_rental_invoice(
            contract_id=self.contract.contract_no,
            user=self.accountant
        )
        initial_net = invoice.net_total_payable

        # 1. Partial payment
        payment1 = record_invoice_payment(
            invoice_id=invoice.invoice_no,
            payment_data={
                'amount': Decimal("200000.00"),
                'payment_method': Payment.PaymentMethod.BANK_TRANSFER,
                'reference_number': 'TXN-001',
                'notes': 'Part payment 1'
            },
            user=self.accountant
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal("200000.00"))
        self.assertEqual(invoice.status, Invoice.Status.PARTIALLY_PAID)

        # 2. Final settlement payment
        payment2 = record_invoice_payment(
            invoice_id=invoice.invoice_no,
            payment_data={
                'amount': invoice.balance_due,
                'payment_method': Payment.PaymentMethod.CHEQUE,
                'reference_number': 'CHQ-002',
            },
            user=self.accountant
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, initial_net)
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(invoice.balance_due, Decimal("0.00"))

        # Customer balance should be 0
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.current_outstanding_balance, Decimal("0.00"))

    def test_deposit_refund_service(self):
        deposit = SecurityDeposit.objects.create(
            deposit_id="DEP-2026-SRV-001",
            contract=self.contract,
            customer=self.customer,
            deposit_amount=Decimal("100000.00"),
            received_date=date(2026, 11, 1),
            status=SecurityDeposit.Status.HELD
        )

        refund_payment = process_deposit_refund(
            deposit_id=deposit.deposit_id,
            refund_data={
                'refund_amount': Decimal("100000.00"),
                'payment_method': Payment.PaymentMethod.BANK_TRANSFER,
                'reference_number': 'REF-001'
            },
            user=self.accountant
        )

        deposit.refresh_from_db()
        self.assertEqual(deposit.refunded_amount, Decimal("100000.00"))
        self.assertEqual(deposit.status, SecurityDeposit.Status.REFUNDED)
        self.assertEqual(refund_payment.payment_type, Payment.PaymentType.DEPOSIT_REFUND)

    def test_invoice_views_and_access_control(self):
        invoice = generate_final_rental_invoice(
            contract_id=self.contract.contract_no,
            user=self.accountant
        )

        # Unauthenticated access redirects to login
        res = self.client.get('/finance/invoices/')
        self.assertEqual(res.status_code, 302)

        # Authenticated as Accountant
        self.client.force_login(self.accountant)

        # List view
        res = self.client.get('/finance/invoices/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, invoice.invoice_no)

        # Detail view
        res = self.client.get(f'/finance/invoices/{invoice.invoice_no}/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, invoice.customer.company_name)

        # PDF view
        res = self.client.get(f'/finance/invoices/{invoice.invoice_no}/pdf/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')

        # Deposit Ledger view
        res = self.client.get('/finance/deposits/')
        self.assertEqual(res.status_code, 200)

        # Payment Create View (POST)
        res = self.client.post(f'/finance/invoices/{invoice.invoice_no}/pay/', {
            'amount': '50000.00',
            'payment_date': str(timezone.now().date()),
            'payment_type': 'RENTAL_PAYMENT',
            'payment_method': 'CASH',
            'reference_number': 'CASH-REC-01',
            'notes': 'Direct cash collection'
        })
        self.assertEqual(res.status_code, 302)
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal("50000.00"))
