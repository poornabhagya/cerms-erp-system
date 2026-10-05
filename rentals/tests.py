from decimal import Decimal
from django.test import TestCase

from rentals.models import Customer, ProjectSite
from rentals.services import validate_customer_credit_limit


class CustomerCreditLimitServiceTests(TestCase):
    """Unit tests for Section 3.2: Customer Business Logic & Credit Limit Verification."""

    def setUp(self):
        self.customer = Customer.objects.create(
            customer_code='CUST-2026-001',
            company_name='Access Engineering PLC',
            contact_person='Sunil Jayawardena',
            phone='+94 11 234 5678',
            email='finance@accesseng.lk',
            billing_address='No. 278, Union Place, Colombo 02, Sri Lanka',
            vat_tax_number='VAT-102938475',
            credit_limit=Decimal('5000000.00'),
            current_outstanding_balance=Decimal('1500000.00'),
            status=Customer.Status.ACTIVE
        )

        self.site = ProjectSite.objects.create(
            project_code='PRJ-COL-001',
            customer=self.customer,
            project_name='Port City Elevated Highway Project',
            site_address='Marine Drive, Colombo 01',
            gps_coordinates='6.9271,79.8612',
            site_contact_person='Eng. Nimal Rathnayake',
            site_contact_phone='+94 77 123 4567',
            status=ProjectSite.Status.ACTIVE
        )

    def test_customer_model_properties(self):
        self.assertEqual(str(self.customer), "CUST-2026-001 - Access Engineering PLC")
        self.assertEqual(self.customer.available_credit, Decimal('3500000.00'))
        self.assertTrue(self.customer.is_active)

    def test_project_site_model_properties(self):
        self.assertEqual(str(self.site), "PRJ-COL-001 - Port City Elevated Highway Project (Access Engineering PLC)")
        self.assertEqual(self.customer.project_sites.count(), 1)

    def test_credit_check_well_under_limit(self):
        """1.5M outstanding + 1.0M quotation = 2.5M < 5.0M limit (APPROVED)."""
        res = validate_customer_credit_limit(self.customer, Decimal('1000000.00'))
        self.assertTrue(res['is_valid'])
        self.assertFalse(res['requires_approval'])
        self.assertEqual(res['decision'], 'APPROVED')
        self.assertEqual(res['projected_balance'], Decimal('2500000.00'))
        self.assertEqual(res['exceeded_by'], Decimal('0.00'))

    def test_credit_check_exactly_at_limit(self):
        """1.5M outstanding + 3.5M quotation = 5.0M == 5.0M limit (APPROVED)."""
        res = validate_customer_credit_limit(self.customer, Decimal('3500000.00'))
        self.assertTrue(res['is_valid'])
        self.assertFalse(res['requires_approval'])
        self.assertEqual(res['decision'], 'APPROVED')
        self.assertEqual(res['projected_balance'], Decimal('5000000.00'))
        self.assertEqual(res['exceeded_by'], Decimal('0.00'))

    def test_credit_check_exceeding_limit(self):
        """1.5M outstanding + 4.0M quotation = 5.5M > 5.0M limit (REQUIRES_MANAGEMENT_APPROVAL by 500K)."""
        res = validate_customer_credit_limit(self.customer, Decimal('4000000.00'))
        self.assertFalse(res['is_valid'])
        self.assertTrue(res['requires_approval'])
        self.assertEqual(res['decision'], 'REQUIRES_MANAGEMENT_APPROVAL')
        self.assertEqual(res['projected_balance'], Decimal('5500000.00'))
        self.assertEqual(res['exceeded_by'], Decimal('500000.00'))
        self.assertIn("Credit limit exceeded by Rs. 500,000.00", res['message'])

    def test_credit_check_blocked_account(self):
        """BLOCKED account must be blocked and require override regardless of amount."""
        self.customer.status = Customer.Status.BLOCKED
        self.customer.save()

        res = validate_customer_credit_limit(self.customer, Decimal('100000.00'))
        self.assertFalse(res['is_valid'])
        self.assertTrue(res['requires_approval'])
        self.assertEqual(res['decision'], 'BLOCKED')
        self.assertIn("ON CREDIT HOLD / BLOCKED", res['message'])

    def test_credit_check_inactive_account(self):
        """INACTIVE account must be flagged for reactivation."""
        self.customer.status = Customer.Status.INACTIVE
        self.customer.save()

        res = validate_customer_credit_limit(self.customer, Decimal('50000.00'))
        self.assertFalse(res['is_valid'])
        self.assertTrue(res['requires_approval'])
        self.assertEqual(res['decision'], 'INACTIVE')
        self.assertIn("INACTIVE", res['message'])

    def test_credit_check_zero_credit_limit(self):
        """Zero credit limit indicates prepayment/cash customer."""
        cash_customer = Customer.objects.create(
            customer_code='CUST-2026-002',
            company_name='Walk-in Contractor Ltd',
            contact_person='Ajith Kumara',
            phone='+94 71 999 8888',
            email='ajith@walkin.lk',
            billing_address='Kandy, Sri Lanka',
            credit_limit=Decimal('0.00'),
            current_outstanding_balance=Decimal('0.00'),
            status=Customer.Status.ACTIVE
        )

        res = validate_customer_credit_limit(cash_customer, Decimal('75000.00'))
        self.assertTrue(res['is_valid'])
        self.assertFalse(res['requires_approval'])
        self.assertEqual(res['decision'], 'APPROVED')
        self.assertIn("Zero Credit Line", res['message'])
