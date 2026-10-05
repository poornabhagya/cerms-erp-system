"""
CERMS Role-Based Access Control (RBAC) Permissions & Mixins.
Reference: docs/03_ROLES_AND_PERMISSIONS.md & docs/23_PHASE_1_ROADMAP.md
"""

from functools import wraps
from typing import Iterable, Union

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from rest_framework.permissions import BasePermission

from .models import User


# ============================================================================
# 1. CLASS-BASED VIEW (CBV) MIXINS
# ============================================================================

class RoleRequiredMixin(AccessMixin):
    """
    CBV mixin that verifies the authenticated user has one of the required roles.
    Superusers and Administrators bypass role checks by default unless strict_mode=True.
    """
    allowed_roles: Iterable[str] = ()
    allow_admin_override: bool = True
    permission_denied_message: str = "You do not have permission to access this resource."

    def get_allowed_roles(self) -> Iterable[str]:
        return self.allowed_roles

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        user: User = request.user
        allowed_roles = self.get_allowed_roles()

        # Check for admin bypass
        if self.allow_admin_override and (user.is_superuser or user.role == User.Role.ADMINISTRATOR):
            return super().dispatch(request, *args, **kwargs)

        if user.role not in allowed_roles:
            raise PermissionDenied(self.permission_denied_message)

        return super().dispatch(request, *args, **kwargs)


class AdminOnlyMixin(RoleRequiredMixin):
    """Restricts view access strictly to Administrators / Superusers."""
    allowed_roles = (User.Role.ADMINISTRATOR,)


class ManagementOrAdminRequiredMixin(RoleRequiredMixin):
    """Allows access to Management executives and Administrators."""
    allowed_roles = (User.Role.ADMINISTRATOR, User.Role.MANAGEMENT)


class RentalOfficerRequiredMixin(RoleRequiredMixin):
    """Allows access to Rental Officers, Management, and Administrators."""
    allowed_roles = (User.Role.RENTAL_OFFICER, User.Role.MANAGEMENT, User.Role.ADMINISTRATOR)


class OperationsOfficerRequiredMixin(RoleRequiredMixin):
    """Allows access to Operations Officers, Management, and Administrators."""
    allowed_roles = (User.Role.OPERATIONS_OFFICER, User.Role.MANAGEMENT, User.Role.ADMINISTRATOR)


class WorkshopManagerRequiredMixin(RoleRequiredMixin):
    """Allows access to Workshop Managers, Management, and Administrators."""
    allowed_roles = (User.Role.WORKSHOP_MANAGER, User.Role.MANAGEMENT, User.Role.ADMINISTRATOR)


class AccountantRequiredMixin(RoleRequiredMixin):
    """Allows access to Accountants, Management, and Administrators."""
    allowed_roles = (User.Role.ACCOUNTANT, User.Role.MANAGEMENT, User.Role.ADMINISTRATOR)


class StorekeeperRequiredMixin(RoleRequiredMixin):
    """Allows access to Storekeepers, Workshop Managers, and Administrators."""
    allowed_roles = (User.Role.STOREKEEPER, User.Role.WORKSHOP_MANAGER, User.Role.ADMINISTRATOR)


class FieldOfficerRequiredMixin(RoleRequiredMixin):
    """Allows access to Field Officers, Operations Officers, and Administrators."""
    allowed_roles = (User.Role.FIELD_OFFICER, User.Role.OPERATIONS_OFFICER, User.Role.ADMINISTRATOR)


# ============================================================================
# 2. FUNCTION-BASED VIEW (FBV) DECORATORS
# ============================================================================

def role_required(allowed_roles: Union[str, Iterable[str]], allow_admin_override: bool = True):
    """
    Decorator for views that checks whether a user has a specific role,
    redirecting to the log-in page if not logged in, or raising PermissionDenied.
    """
    if isinstance(allowed_roles, str):
        roles = (allowed_roles,)
    else:
        roles = tuple(allowed_roles)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not request.user.is_authenticated:
                return redirect('users:login')

            user: User = request.user
            if allow_admin_override and (user.is_superuser or user.role == User.Role.ADMINISTRATOR):
                return view_func(request, *args, **kwargs)

            if user.role in roles:
                return view_func(request, *args, **kwargs)

            raise PermissionDenied("You do not have permission to access this resource.")

        return _wrapped_view

    return decorator


def admin_required(view_func):
    """Decorator restricting view access strictly to Administrators."""
    return role_required((User.Role.ADMINISTRATOR,))(view_func)


def management_or_admin_required(view_func):
    """Decorator allowing access to Management and Administrators."""
    return role_required((User.Role.MANAGEMENT, User.Role.ADMINISTRATOR))(view_func)


def rental_officer_required(view_func):
    """Decorator allowing access to Rental Officers, Management, and Administrators."""
    return role_required((User.Role.RENTAL_OFFICER, User.Role.MANAGEMENT, User.Role.ADMINISTRATOR))(view_func)


def accountant_required(view_func):
    """Decorator allowing access to Accountants, Management, and Administrators."""
    return role_required((User.Role.ACCOUNTANT, User.Role.MANAGEMENT, User.Role.ADMINISTRATOR))(view_func)


# ============================================================================
# 3. DJANGO REST FRAMEWORK (DRF) PERMISSION CLASSES
# ============================================================================

class HasRolePermission(BasePermission):
    """
    DRF permission class that validates request.user against a list of allowed roles.
    """
    allowed_roles: Iterable[str] = ()

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if request.user.is_superuser or request.user.role == User.Role.ADMINISTRATOR:
            return True

        allowed = getattr(view, 'allowed_roles', self.allowed_roles)
        return request.user.role in allowed


class IsAdministrator(BasePermission):
    """DRF permission allowing only Administrators."""
    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or request.user.role == User.Role.ADMINISTRATOR)
        )


class IsManagementOrAdmin(BasePermission):
    """DRF permission allowing Management and Administrators."""
    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or request.user.role in (User.Role.MANAGEMENT, User.Role.ADMINISTRATOR))
        )


class IsFieldOfficer(BasePermission):
    """DRF permission allowing Field Officers and Administrators for mobile APIs."""
    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or request.user.role in (User.Role.FIELD_OFFICER, User.Role.OPERATIONS_OFFICER, User.Role.ADMINISTRATOR))
        )


class IsAccountant(BasePermission):
    """DRF permission allowing Accountants and Administrators."""
    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or request.user.role in (User.Role.ACCOUNTANT, User.Role.MANAGEMENT, User.Role.ADMINISTRATOR))
        )
