from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import Group

from users.models import User
from fleet.models import Category, Equipment, RentalRate


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
