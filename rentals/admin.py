from django.contrib import admin
from .models import Customer, ProjectSite


class ProjectSiteInline(admin.TabularInline):
    model = ProjectSite
    extra = 1
    fields = ('project_code', 'project_name', 'site_address', 'gps_coordinates', 'site_contact_person', 'site_contact_phone', 'status')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'customer_code',
        'company_name',
        'contact_person',
        'phone',
        'email',
        'credit_limit',
        'current_outstanding_balance',
        'status',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('customer_code', 'company_name', 'contact_person', 'phone', 'email', 'vat_tax_number')
    inlines = [ProjectSiteInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProjectSite)
class ProjectSiteAdmin(admin.ModelAdmin):
    list_display = (
        'project_code',
        'project_name',
        'customer',
        'site_contact_person',
        'site_contact_phone',
        'status',
    )
    list_filter = ('status', 'customer')
    search_fields = ('project_code', 'project_name', 'site_address', 'site_contact_person', 'customer__company_name')
    readonly_fields = ('created_at', 'updated_at')
