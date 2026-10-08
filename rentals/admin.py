from django.contrib import admin
from .models import Customer, ProjectSite, Quotation, QuotationItem, RentalContract, RentalContractItem, DispatchReturn


class ProjectSiteInline(admin.TabularInline):
    model = ProjectSite
    extra = 1
    fields = ('project_code', 'project_name', 'site_contact_person', 'site_contact_phone', 'status')
    show_change_link = True


class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 1
    fields = ('equipment', 'start_date', 'end_date', 'rate_type', 'rate_applied', 'subtotal_amount')
    raw_id_fields = ('equipment',)
    show_change_link = True


class RentalContractItemInline(admin.TabularInline):
    model = RentalContractItem
    extra = 1
    fields = ('equipment', 'start_date', 'end_date', 'rate_type', 'rate_applied', 'subtotal_amount')
    raw_id_fields = ('equipment',)
    show_change_link = True


class DispatchReturnInline(admin.TabularInline):
    model = DispatchReturn
    extra = 0
    fields = ('transaction_id', 'equipment', 'dispatch_datetime', 'dispatch_hour_meter', 'return_datetime', 'return_hour_meter', 'damage_reported')
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


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = (
        'quotation_no',
        'customer',
        'start_date',
        'end_date',
        'subtotal_amount',
        'grand_total_amount',
        'status',
        'approved_by',
        'created_at'
    )
    list_filter = ('status', 'rate_type', 'created_at')
    search_fields = ('quotation_no', 'customer__company_name', 'items__equipment__asset_code', 'items__equipment__equipment_name')
    raw_id_fields = ('customer', 'project_site', 'approved_by')
    inlines = [QuotationItemInline]
    ordering = ('-created_at',)


@admin.register(RentalContract)
class RentalContractAdmin(admin.ModelAdmin):
    list_display = (
        'contract_no',
        'quotation',
        'customer',
        'equipment',
        'contract_start_date',
        'contract_end_date',
        'billing_cycle',
        'status',
        'created_at'
    )
    list_filter = ('status', 'billing_cycle', 'created_at')
    search_fields = ('contract_no', 'customer__company_name', 'equipment__asset_code', 'quotation__quotation_no')
    raw_id_fields = ('quotation', 'customer', 'project_site', 'equipment')
    inlines = [RentalContractItemInline, DispatchReturnInline]
    ordering = ('-contract_start_date',)


@admin.register(DispatchReturn)
class DispatchReturnAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id',
        'contract',
        'equipment',
        'dispatch_datetime',
        'dispatch_hour_meter',
        'return_datetime',
        'return_hour_meter',
        'damage_reported',
        'excess_hours_calculated'
    )
    list_filter = ('damage_reported', 'dispatch_datetime', 'return_datetime')
    search_fields = ('transaction_id', 'contract__contract_no', 'equipment__asset_code')
    raw_id_fields = ('contract', 'equipment', 'dispatch_officer', 'return_officer')
    ordering = ('-dispatch_datetime',)
