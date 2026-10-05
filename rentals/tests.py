from decimal import Decimal
from django.test import TestCase

from rentals.models import Customer, ProjectSite
from rentals.services import validate_customer_credit_limit


class CustomerAndSiteServiceTests(TestCase):
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

    def test_credit_limit_validation_within_limit(self):
        res = validate_customer_credit_limit(self.customer, Decimal('2000000.00'))
        self.assertTrue(res['is_valid'])
        self.assertFalse(res['requires_approval'])
        self.assertEqual(res['projected_balance'], Decimal('3500000.00'))

    def test_credit_limit_validation_exceeded(self):
        # 1.5M existing + 4.0M new = 5.5M (exceeds 5.0M limit by 500K)
        res = validate_customer_credit_limit(self.customer, Decimal('4000000.00'))
        self.assertFalse(res['is_valid'])
        self.assertTrue(res['requires_approval'])
        self.assertEqual(res['exceeded_by'], Decimal('500000.00'))

    def test_credit_limit_blocked_customer(self):
        self.customer.status = Customer.Status.BLOCKED
        self.customer.save()

        res = validate_customer_credit_limit(self.customer, Decimal('100000.00'))
        self.assertFalse(res['is_valid'])
        self.assertTrue(res['requires_approval'])
