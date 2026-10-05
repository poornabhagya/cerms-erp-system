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
