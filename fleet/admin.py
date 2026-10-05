from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Category, Equipment, RentalRate


class RentalRateInline(admin.TabularInline):
    model = RentalRate
    extra = 1
    fields = (
        'daily_rate',
        'hourly_rate',
        'weekly_rate',
        'monthly_rate',
        'overtime_hourly_rate',
        'minimum_rental_hours',
        'effective_from',
        'is_active',
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at', 'updated_at')
    search_fields = ('name', 'code')
    prepopulated_fields = {'code': ('name',)}


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        'asset_code',
        'equipment_name',
        'category',
        'brand',
        'model_number',
        'current_hour_meter',
        'status',
        'purchase_cost',
    )
    list_filter = ('category', 'status', 'brand', 'manufacture_year')
    search_fields = ('asset_code', 'equipment_name', 'serial_number', 'brand', 'model_number')
    inlines = [RentalRateInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RentalRate)
class RentalRateAdmin(admin.ModelAdmin):
    list_display = (
        'equipment',
        'daily_rate',
        'hourly_rate',
        'weekly_rate',
        'monthly_rate',
        'is_active',
        'effective_from',
    )
    list_filter = ('is_active', 'effective_from')
    search_fields = ('equipment__asset_code', 'equipment__equipment_name')
