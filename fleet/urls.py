from django.urls import path
from .views import (
    CategoryListView,
    CategoryCreateView,
    CategoryUpdateView,
    CategoryCreateUpdateView,
    EquipmentListView,
    EquipmentDetailView,
    EquipmentCreateView,
    EquipmentUpdateView,
    EquipmentStatusUpdateView,
)

app_name = 'fleet'

urlpatterns = [
    # Category Master Endpoints
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/create/', CategoryCreateView.as_view(), name='category_create'),
    path('categories/<str:code>/edit/', CategoryUpdateView.as_view(), name='category_update'),

    # Equipment Master Endpoints
    path('', EquipmentListView.as_view(), name='equipment_list'),
    path('create/', EquipmentCreateView.as_view(), name='equipment_create'),
    path('<str:asset_code>/', EquipmentDetailView.as_view(), name='equipment_detail'),
    path('<str:asset_code>/edit/', EquipmentUpdateView.as_view(), name='equipment_update'),
    path('<str:asset_code>/status/', EquipmentStatusUpdateView.as_view(), name='equipment_status_update'),
]

