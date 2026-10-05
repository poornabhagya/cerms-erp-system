from django.contrib import admin
from .models import Customer, ProjectSite


class ProjectSiteInline(admin.TabularInline):
    model = ProjectSite
    extra = 1
    fields = ('project_code', 'project_name', 'site_contact_person', 'site_contact_phone', 'status')
    show_change_link = True


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
        'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('customer_code', 'company_name', 'contact_person', 'phone', 'email', 'vat_tax_number')
    ordering = ('company_name',)
    inlines = [ProjectSiteInline]
    fieldsets = (
        ('Company & Identification', {
            'fields': ('customer_code', 'company_name', 'vat_tax_number', 'status')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'phone', 'email', 'billing_address')
        }),
        ('Credit & Financial Standing', {
            'fields': ('credit_limit', 'current_outstanding_balance')
        }),
    )


@admin.register(ProjectSite)
class ProjectSiteAdmin(admin.ModelAdmin):
    list_display = (
        'project_code',
        'project_name',
        'customer',
        'site_contact_person',
        'site_contact_phone',
        'status',
        'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('project_code', 'project_name', 'customer__company_name', 'site_contact_person', 'site_contact_phone')
    raw_id_fields = ('customer',)
    ordering = ('project_name',)
