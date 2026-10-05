from django.urls import path
from .views import (
    CustomerListView,
    CustomerDetailView,
    CustomerCreateView,
    CustomerUpdateView,
    ProjectSiteCreateView,
    ProjectSiteUpdateView,
)

app_name = 'rentals'

urlpatterns = [
    # Customer Master URLs
    path('customers/', CustomerListView.as_view(), name='customer_list'),
    path('customers/create/', CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<str:customer_code>/', CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<str:customer_code>/edit/', CustomerUpdateView.as_view(), name='customer_update'),

    # Project Sites URLs
    path('sites/create/', ProjectSiteCreateView.as_view(), name='projectsite_create'),
    path('sites/<str:project_code>/edit/', ProjectSiteUpdateView.as_view(), name='projectsite_update'),
]
