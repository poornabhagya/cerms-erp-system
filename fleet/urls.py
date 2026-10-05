from django.urls import path
from .views import (
    EquipmentListView,
    EquipmentDetailView,
    EquipmentCreateView,
    EquipmentUpdateView,
    EquipmentStatusUpdateView,
)

app_name = 'fleet'

urlpatterns = [
    path('', EquipmentListView.as_view(), name='equipment_list'),
    path('create/', EquipmentCreateView.as_view(), name='equipment_create'),
    path('<str:asset_code>/', EquipmentDetailView.as_view(), name='equipment_detail'),
    path('<str:asset_code>/edit/', EquipmentUpdateView.as_view(), name='equipment_update'),
    path('<str:asset_code>/status/', EquipmentStatusUpdateView.as_view(), name='equipment_status_update'),
]
