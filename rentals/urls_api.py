"""
Rentals REST API v1 Routing Configuration
Reference: docs/12_API_AND_REST_STANDARDS.md & docs/23_PHASE_1_ROADMAP.md (Step 6.1)
"""

from django.urls import path
from rentals.api import CalendarEventsAPIView, EquipmentAvailabilityCheckAPIView

urlpatterns = [
    path('', CalendarEventsAPIView.as_view(), name='api_calendar_events_root'),
    path('calendar-events/', CalendarEventsAPIView.as_view(), name='api_calendar_events'),
    path('check-availability/', EquipmentAvailabilityCheckAPIView.as_view(), name='api_check_availability'),
]
