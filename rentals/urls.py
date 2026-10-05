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
]
