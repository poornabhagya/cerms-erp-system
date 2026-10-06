from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # Invoicing Command Center
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<str:invoice_no>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<str:invoice_no>/pdf/', views.InvoicePDFDownloadView.as_view(), name='invoice_pdf'),
    path('invoices/<str:invoice_no>/pay/', views.PaymentCreateView.as_view(), name='invoice_payment'),
    path('contracts/<str:contract_no>/generate-invoice/', views.GenerateInvoiceFromContractView.as_view(), name='generate_contract_invoice'),

    # Payment Entries
    path('payments/create/', views.PaymentCreateView.as_view(), name='payment_create'),

    # Security Deposit Escrow Ledger
    path('deposits/', views.SecurityDepositLedgerView.as_view(), name='deposit_ledger'),
    path('deposits/<str:deposit_id>/refund/', views.DepositRefundView.as_view(), name='deposit_refund'),
]
