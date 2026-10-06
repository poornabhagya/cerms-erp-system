from django.contrib import admin
from .models import Invoice, Payment, SecurityDeposit


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_no',
        'customer',
        'contract',
        'invoice_date',
        'due_date',
        'net_total_payable',
        'paid_amount',
        'status',
    )
    list_filter = ('status', 'invoice_date', 'due_date')
    search_fields = ('invoice_no', 'customer__company_name', 'contract__contract_no')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-invoice_date', '-created_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'payment_id',
        'customer',
        'invoice',
        'amount',
        'payment_date',
        'payment_type',
        'payment_method',
        'reference_number',
    )
    list_filter = ('payment_type', 'payment_method', 'payment_date')
    search_fields = ('payment_id', 'customer__company_name', 'reference_number', 'invoice__invoice_no')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-payment_date', '-created_at')


@admin.register(SecurityDeposit)
class SecurityDepositAdmin(admin.ModelAdmin):
    list_display = (
        'deposit_id',
        'contract',
        'customer',
        'deposit_amount',
        'received_date',
        'deducted_amount',
        'refunded_amount',
        'status',
    )
    list_filter = ('status', 'received_date')
    search_fields = ('deposit_id', 'contract__contract_no', 'customer__company_name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
