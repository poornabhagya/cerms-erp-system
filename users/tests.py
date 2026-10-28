from django.test import TestCase, RequestFactory
from django.core.exceptions import PermissionDenied
from django.views.generic import View
from django.http import HttpResponse

from users.models import User
from users.permissions import (
    RoleRequiredMixin,
    RentalOfficerRequiredMixin,
    AccountantRequiredMixin,
    role_required,
)


class DummyRentalView(RentalOfficerRequiredMixin, View):
    def get(self, request):
        return HttpResponse("Rental View OK")


class RBACPermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpassword123',
            role=User.Role.ADMINISTRATOR
        )
        self.rental_user = User.objects.create_user(
            username='rental_test',
            email='rental@test.com',
            password='testpassword123',
            role=User.Role.RENTAL_OFFICER
        )
        self.field_user = User.objects.create_user(
            username='field_test',
            email='field@test.com',
            password='testpassword123',
            role=User.Role.FIELD_OFFICER
        )

    def test_user_role_helper_properties(self):
        self.assertTrue(self.admin_user.is_administrator)
        self.assertTrue(self.admin_user.is_management)
        self.assertTrue(self.rental_user.is_rental_officer)
        self.assertFalse(self.rental_user.is_accountant)
        self.assertTrue(self.field_user.is_field_officer)

    def test_cbv_mixin_authorized_access(self):
        request = self.factory.get('/dummy-rental/')
        request.user = self.rental_user
        response = DummyRentalView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_cbv_mixin_unauthorized_access(self):
        request = self.factory.get('/dummy-rental/')
        request.user = self.field_user
        with self.assertRaises(PermissionDenied):
            DummyRentalView.as_view()(request)

    def test_fbv_decorator_permission(self):
        @role_required([User.Role.ACCOUNTANT])
        def dummy_finance_view(request):
            return HttpResponse("Finance OK")

        request = self.factory.get('/dummy-finance/')
        request.user = self.rental_user
        with self.assertRaises(PermissionDenied):
            dummy_finance_view(request)


class CoreRolesFixtureTests(TestCase):
    """
    Validates that core_roles.json loads cleanly and that all 8 organizational
    groups receive the correct granular Django model permissions per docs/23_PHASE_1_ROADMAP.md.
    """

    def setUp(self):
        from django.core.management import call_command
        call_command('loaddata', 'users/fixtures/core_roles.json')

    def test_all_eight_groups_exist_and_have_permissions(self):
        from django.contrib.auth.models import Group
        expected_groups = [
            'Administrator',
            'Management',
            'Rental Officer',
            'Operations Officer',
            'Workshop Manager',
            'Accountant',
            'Storekeeper',
            'Field Officer',
        ]
        self.assertEqual(Group.objects.count(), 8)
        for name in expected_groups:
            group = Group.objects.get(name=name)
            self.assertTrue(group.permissions.exists(), f"Group {name} has no permissions!")

    def test_administrator_has_full_crud_permissions(self):
        from django.contrib.auth.models import Group
        admin_group = Group.objects.get(name='Administrator')
        user = User.objects.create_user(
            username='admin_fixture_user',
            email='admin_fix@test.com',
            password='password123',
            role=User.Role.ADMINISTRATOR
        )
        user.groups.add(admin_group)
        user = User.objects.get(pk=user.pk)

        # Check full permissions across apps
        self.assertTrue(user.has_perm('fleet.delete_equipment'))
        self.assertTrue(user.has_perm('rentals.delete_quotation'))
        self.assertTrue(user.has_perm('rentals.delete_rentalcontract'))
        self.assertTrue(user.has_perm('finance.delete_invoice'))
        self.assertTrue(user.has_perm('users.delete_user'))
        self.assertTrue(user.has_perm('auth.delete_group'))

    def test_rental_officer_permissions_and_restrictions(self):
        from django.contrib.auth.models import Group
        ro_group = Group.objects.get(name='Rental Officer')
        user = User.objects.create_user(
            username='ro_fixture_user',
            email='ro_fix@test.com',
            password='password123',
            role=User.Role.RENTAL_OFFICER
        )
        user.groups.add(ro_group)
        user = User.objects.get(pk=user.pk)

        # Authorized actions
        self.assertTrue(user.has_perm('rentals.add_customer'))
        self.assertTrue(user.has_perm('rentals.change_customer'))
        self.assertTrue(user.has_perm('rentals.view_customer'))
        self.assertTrue(user.has_perm('rentals.add_quotation'))
        self.assertTrue(user.has_perm('rentals.change_quotation'))
        self.assertTrue(user.has_perm('rentals.add_rentalcontract'))
        self.assertTrue(user.has_perm('rentals.change_rentalcontract'))
        self.assertTrue(user.has_perm('fleet.add_rentalrate'))
        self.assertTrue(user.has_perm('fleet.view_equipment'))

        # Restricted actions (cannot delete, cannot settle payments)
        self.assertFalse(user.has_perm('rentals.delete_quotation'))
        self.assertFalse(user.has_perm('rentals.delete_rentalcontract'))
        self.assertFalse(user.has_perm('finance.add_payment'))
        self.assertFalse(user.has_perm('finance.change_invoice'))

    def test_accountant_permissions_and_restrictions(self):
        from django.contrib.auth.models import Group
        acc_group = Group.objects.get(name='Accountant')
        user = User.objects.create_user(
            username='acc_fixture_user',
            email='acc_fix@test.com',
            password='password123',
            role=User.Role.ACCOUNTANT
        )
        user.groups.add(acc_group)
        user = User.objects.get(pk=user.pk)

        # Authorized actions
        self.assertTrue(user.has_perm('finance.add_invoice'))
        self.assertTrue(user.has_perm('finance.change_invoice'))
        self.assertTrue(user.has_perm('finance.add_payment'))
        self.assertTrue(user.has_perm('finance.add_securitydeposit'))
        self.assertTrue(user.has_perm('rentals.change_customer'))  # credit limit adjustment
        self.assertTrue(user.has_perm('rentals.view_rentalcontract'))

        # Restricted actions (cannot create quotations or contracts)
        self.assertFalse(user.has_perm('rentals.add_quotation'))
        self.assertFalse(user.has_perm('rentals.add_rentalcontract'))
        self.assertFalse(user.has_perm('fleet.add_equipment'))

    def test_operations_and_field_officer_permissions(self):
        from django.contrib.auth.models import Group
        ops_group = Group.objects.get(name='Operations Officer')
        field_group = Group.objects.get(name='Field Officer')

        ops_user = User.objects.create_user(
            username='ops_fixture_user',
            email='ops_fix@test.com',
            password='password123',
            role=User.Role.OPERATIONS_OFFICER
        )
        ops_user.groups.add(ops_group)
        ops_user = User.objects.get(pk=ops_user.pk)

        field_user = User.objects.create_user(
            username='field_fixture_user',
            email='field_fix@test.com',
            password='password123',
            role=User.Role.FIELD_OFFICER
        )
        field_user.groups.add(field_group)
        field_user = User.objects.get(pk=field_user.pk)

        # Both have dispatch and return permissions
        self.assertTrue(ops_user.has_perm('rentals.add_dispatchreturn'))
        self.assertTrue(ops_user.has_perm('rentals.change_dispatchreturn'))
        self.assertTrue(field_user.has_perm('rentals.add_dispatchreturn'))
        self.assertTrue(field_user.has_perm('rentals.change_dispatchreturn'))

        # Neither can create financial invoices or quotations
        self.assertFalse(ops_user.has_perm('finance.add_invoice'))
        self.assertFalse(field_user.has_perm('rentals.add_quotation'))

    def test_workshop_manager_permissions(self):
        from django.contrib.auth.models import Group
        wm_group = Group.objects.get(name='Workshop Manager')
        user = User.objects.create_user(
            username='wm_fixture_user',
            email='wm_fix@test.com',
            password='password123',
            role=User.Role.WORKSHOP_MANAGER
        )
        user.groups.add(wm_group)
        user = User.objects.get(pk=user.pk)

        self.assertTrue(user.has_perm('fleet.add_equipment'))
        self.assertTrue(user.has_perm('fleet.change_equipment'))
        self.assertTrue(user.has_perm('fleet.add_category'))
        self.assertTrue(user.has_perm('rentals.view_dispatchreturn'))

        # Cannot modify rental contracts or finance invoices
        self.assertFalse(user.has_perm('rentals.change_rentalcontract'))
        self.assertFalse(user.has_perm('finance.add_invoice'))

