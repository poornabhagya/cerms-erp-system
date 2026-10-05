from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordChangeDoneView,
)
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .forms import UserLoginForm, UserPasswordChangeCustomForm
from .serializers import CustomTokenObtainPairSerializer, UserSerializer


# ============================================================================
# 1. WEB UI AUTHENTICATION VIEWS (Session-Based)
# ============================================================================

class UserLoginView(LoginView):
    """Session login view with Bootstrap 5 styling and flash notifications."""
    authentication_form = UserLoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().username}!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('users:profile')


class UserLogoutView(LogoutView):
    """Session logout view redirecting to login page with notice."""
    next_page = reverse_lazy('users:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "You have been successfully signed out.")
        return super().dispatch(request, *args, **kwargs)


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Self-service password update view."""
    form_class = UserPasswordChangeCustomForm
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('users:password_change_done')

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed successfully.")
        return super().form_valid(form)


class UserPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    """Confirmation page post password update."""
    template_name = 'users/password_change_done.html'


class UserProfileView(LoginRequiredMixin, TemplateView):
    """Dashboard profile overview for currently authenticated user."""
    template_name = 'users/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_profile'] = self.request.user
        return context


# ============================================================================
# 2. REST & JWT API AUTHENTICATION ENDPOINTS (Stateless / Mobile)
# ============================================================================

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    JWT Token generation endpoint for Mobile Field Officers and External APIs.
    POST /api/v1/auth/token/
    """
    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """
    JWT Token refresh endpoint.
    POST /api/v1/auth/token/refresh/
    """
    pass


class CurrentUserAPIView(APIView):
    """
    Returns profile information for the authenticated token bearer.
    GET /api/v1/auth/me/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            "status": "success",
            "message": "User profile retrieved successfully.",
            "data": serializer.data
        })
