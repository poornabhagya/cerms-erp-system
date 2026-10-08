from django.urls import path
from . import views

app_name = 'rentals'

urlpatterns = [
    # Customer Master Endpoints
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<str:customer_code>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<str:customer_code>/edit/', views.CustomerUpdateView.as_view(), name='customer_update'),

    # Project Site Endpoints
    path('sites/', views.ProjectSiteListView.as_view(), name='site_list'),
    path('sites/create/', views.ProjectSiteCreateView.as_view(), name='site_create'),
    path('sites/<str:project_code>/edit/', views.ProjectSiteUpdateView.as_view(), name='site_update'),
    path('sites/<str:project_code>/delete/', views.ProjectSiteDeleteView.as_view(), name='site_delete'),
    path('api/generate-site-code/', views.ProjectSiteCodeGenerateAPIView.as_view(), name='api_generate_site_code'),

    # Quotation Lifecycle Endpoints
    path('quotations/', views.QuotationListView.as_view(), name='quotation_list'),
    path('quotations/create/', views.QuotationCreateView.as_view(), name='quotation_create'),
    path('quotations/<str:quotation_no>/', views.QuotationDetailView.as_view(), name='quotation_detail'),
    path('quotations/<str:quotation_no>/edit/', views.QuotationUpdateView.as_view(), name='quotation_update'),
    path('quotations/<str:quotation_no>/delete/', views.QuotationDeleteView.as_view(), name='quotation_delete'),
    path('quotations/<str:quotation_no>/transition/', views.QuotationStatusTransitionView.as_view(), name='quotation_transition'),

    # Rental Contract Endpoints
    path('contracts/', views.RentalContractListView.as_view(), name='contract_list'),
    path('contracts/<str:contract_no>/', views.RentalContractDetailView.as_view(), name='contract_detail'),

    # Logistics (Dispatch & Return Handover) Endpoints
    path('contracts/<str:contract_no>/dispatch/', views.DispatchCreateView.as_view(), name='dispatch_create'),
    path('returns/<str:transaction_id>/', views.ReturnCreateView.as_view(), name='return_create'),

    # Interactive Availability Calendar & Visual Scheduling
    path('availability-calendar/', views.AvailabilityCalendarView.as_view(), name='availability_calendar'),
    path('calendar/', views.AvailabilityCalendarView.as_view(), name='calendar'),
    path('calendar-events/', views.CalendarEventsAPIView.as_view(), name='calendar_events_direct'),
    path('api/calendar-events/', views.CalendarEventsAPIView.as_view(), name='calendar_events_api'),
    path('check-availability/', views.EquipmentAvailabilityCheckAPIView.as_view(), name='check_availability_direct'),
    path('api/check-availability/', views.EquipmentAvailabilityCheckAPIView.as_view(), name='check_availability_api'),
]
