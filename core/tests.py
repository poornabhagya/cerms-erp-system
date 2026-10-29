from decimal import Decimal
from datetime import date
from django.test import TestCase, RequestFactory
from django.core.management import call_command
from django.contrib.auth.models import Group, AnonymousUser
from django.http import HttpResponse

from users.models import User
from fleet.models import Category, Equipment, RentalRate
from rentals.models import Customer
from core.middleware import (
    get_current_user,
    set_current_user,
    set_audit_user,
    CurrentUserMiddleware,
)


class SeedInitialDataCommandTests(TestCase):
    def test_seed_command_execution(self):
        """Verify seed_initial_data executes cleanly and populates all models."""
        call_command('seed_initial_data')

        # Check groups
        self.assertEqual(Group.objects.count(), 8)

        # Check users
        self.assertTrue(User.objects.filter(username='admin').exists())
        self.assertTrue(User.objects.filter(username='rental_officer').exists())

        # Check categories
        self.assertGreaterEqual(Category.objects.count(), 2)
        self.assertTrue(Category.objects.filter(code='EXC').exists())
        self.assertTrue(Category.objects.filter(code='GEN').exists())

        # Check equipment assets and rates
        self.assertGreaterEqual(Equipment.objects.count(), 2)
        cat_exc = Equipment.objects.get(asset_code='EQ-CAT-320-001')
        self.assertEqual(cat_exc.rental_rates.filter(is_active=True).count(), 1)

        # Verify idempotency by calling a second time
        call_command('seed_initial_data')
        self.assertEqual(Group.objects.count(), 8)
        self.assertEqual(Equipment.objects.count(), 4)


class TimeStampedModelAuditabilityTestCase(TestCase):
    """
    Comprehensive test coverage for TimeStampedModel created_by audit field
    and CurrentUserMiddleware automatic population.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.user1 = User.objects.create_user(
            username='officer1',
            email='officer1@cerms.com',
            password='TestPassword123!',
            role=User.Role.RENTAL_OFFICER,
            employee_id='EMP-TEST-001'
        )
        self.user2 = User.objects.create_user(
            username='officer2',
            email='officer2@cerms.com',
            password='TestPassword123!',
            role=User.Role.OPERATIONS_OFFICER,
            employee_id='EMP-TEST-002'
        )

    def test_created_by_automatically_populated_via_context(self):
        """Verify created_by is automatically set to the active user in context."""
        with set_audit_user(self.user1):
            cat = Category.objects.create(name='Heavy Haulers')
            self.assertEqual(cat.created_by, self.user1)

            cust = Customer.objects.create(
                company_name='Audit Test Corp',
                contact_person='Audit Person',
                phone='0771234567',
                email='audit@corp.com',
                billing_address='Colombo'
            )
            self.assertEqual(cust.created_by, self.user1)

    def test_created_by_explicit_override_preserved(self):
        """Verify explicit created_by argument is respected and not overwritten by context."""
        with set_audit_user(self.user1):
            cat = Category.objects.create(name='Light Machinery', created_by=self.user2)
            self.assertEqual(cat.created_by, self.user2)

    def test_created_by_not_overwritten_on_update(self):
        """Verify created_by remains untouched when modifying existing records."""
        with set_audit_user(self.user1):
            cat = Category.objects.create(name='Trenchers')
            self.assertEqual(cat.created_by, self.user1)

        # Update record under a different user
        with set_audit_user(self.user2):
            cat.name = 'Updated Trenchers'
            cat.save()

            cat.refresh_from_db()
            self.assertEqual(cat.created_by, self.user1)
            self.assertEqual(cat.name, 'Updated Trenchers')

    def test_created_by_none_when_outside_request_context(self):
        """Verify created_by is None if created without user context or explicit user."""
        cat = Category.objects.create(name='Pneumatic Tools')
        self.assertIsNone(cat.created_by)

    def test_middleware_captures_authenticated_user_and_cleans_up(self):
        """Verify CurrentUserMiddleware sets user in context during request and cleans up after."""
        captured_user = []

        def dummy_view(request):
            # Inside the view, save a record
            cat = Category.objects.create(name='Excavation Tools')
            captured_user.append((cat.created_by, get_current_user()))
            return HttpResponse("OK")

        middleware = CurrentUserMiddleware(dummy_view)

        request = self.factory.get('/fleet/categories/')
        request.user = self.user1

        response = middleware(request)
        self.assertEqual(response.status_code, 200)

        # Verify created_by was user1 during execution
        cat_created_by, context_user = captured_user[0]
        self.assertEqual(cat_created_by, self.user1)
        self.assertEqual(context_user, self.user1)

        # Verify context is completely cleaned up after request completes
        self.assertIsNone(get_current_user())

    def test_middleware_handles_anonymous_user(self):
        """Verify CurrentUserMiddleware handles anonymous user gracefully without errors."""
        captured_user = []

        def dummy_view(request):
            captured_user.append(get_current_user())
            return HttpResponse("OK")

        middleware = CurrentUserMiddleware(dummy_view)

        request = self.factory.get('/')
        request.user = AnonymousUser()

        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(captured_user[0])
        self.assertIsNone(get_current_user())
