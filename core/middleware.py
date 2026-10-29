"""
Core Application Middleware & Context Management
Provides thread-safe and async-safe request-level context for audit tracking.
"""

import contextvars
from contextlib import contextmanager

# Context variable holding the currently authenticated User for the active execution context
_current_user = contextvars.ContextVar('current_user', default=None)


def get_current_user():
    """
    Retrieve the currently authenticated user from the active request context.
    Returns None if no user is authenticated or context is outside an HTTP request.
    """
    return _current_user.get()


def set_current_user(user):
    """
    Explicitly set the current user in the active context variable.
    Returns the contextvars Token for later reset.
    """
    return _current_user.set(user)


def reset_current_user(token):
    """Reset the current user context variable using the provided Token."""
    _current_user.reset(token)


@contextmanager
def set_audit_user(user):
    """
    Context manager to explicitly set the auditing user for background tasks,
    services, management commands, or tests.

    Usage:
        with set_audit_user(admin_user):
            Equipment.objects.create(...)
    """
    token = _current_user.set(user)
    try:
        yield
    finally:
        _current_user.reset(token)


class CurrentUserMiddleware:
    """
    Middleware that captures the current authenticated user from request.user
    and stores it in a ContextVar for automatic audit logging in TimeStampedModel.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        token = None
        if user and getattr(user, 'is_authenticated', False):
            token = _current_user.set(user)

        try:
            response = self.get_response(request)
            return response
        finally:
            if token is not None:
                _current_user.reset(token)
            else:
                _current_user.set(None)
