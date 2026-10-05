"""
CERMS Master URL Configuration
Reference: docs/09_PROJECT_STRUCTURE_AND_STANDARDS.md & docs/12_API_AND_REST_STANDARDS.md
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    # Django Admin Panel
    path('admin/', admin.site.urls),

    # Users, RBAC & Authentication (Web & API)
    path('', include('users.urls')),

    # Fleet & Equipment Master Management
    path('fleet/', include('fleet.urls')),

    # Rentals & Customer Management
    path('rentals/', include('rentals.urls')),

    # Root redirect to profile/login
    path('', RedirectView.as_view(pattern_name='users:profile', permanent=False), name='home_redirect'),
]
