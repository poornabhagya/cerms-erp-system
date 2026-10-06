from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, FormView

from users.models import User
from users.permissions import RoleRequiredMixin
from rentals.models import RentalContract, Customer
from .models import Invoice, Payment, SecurityDeposit
from .forms import InvoiceGenerationForm, PaymentForm, SecurityDepositRefundForm
from .services import (
    generate_final_rental_invoice,
    record_invoice_payment,
    process_deposit_refund,
    render_invoice_to_pdf
)


# ==============================================================================
# 1. INVOICE COMMAND CENTER & DETAIL VIEWS
# ==============================================================================

class InvoiceListView(RoleRequiredMixin, ListView):
    """
    Invoicing command center displaying commercial tax invoices, payment lifecycle tabs,
    financial KPI aggregators, due date aging badges, and DataTables integration.
    """
    model = Invoice
    template_name = 'finance/invoice_list.html'
    context_object_name = 'invoice_list'
    paginate_by = 25
    allowed_roles = (
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
        User.Role.RENTAL_OFFICER,
    )

    def get_queryset(self):
        queryset = Invoice.objects.select_related('customer', 'contract', 'contract__equipment')
        search_query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(invoice_no__icontains=search_query) |
                Q(customer__company_name__icontains=search_query) |
                Q(contract__contract_no__icontains=search_query)
            )

        if status_filter == 'OVERDUE':
            today = timezone.now().date()
            queryset = queryset.filter(
                Q(status=Invoice.Status.OVERDUE) |
                (Q(status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID]) & Q(due_date__lt=today))
            )
        elif status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_invoices = Invoice.objects.all()
        today = timezone.now().date()

        context['selected_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')

        # KPI Metrics
        context['total_invoices_count'] = all_invoices.count()
        context['unpaid_count'] = all_invoices.filter(status=Invoice.Status.UNPAID).count()
        context['paid_count'] = all_invoices.filter(status=Invoice.Status.PAID).count()
        context['overdue_count'] = all_invoices.filter(
            Q(status=Invoice.Status.OVERDUE) |
            (Q(status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID]) & Q(due_date__lt=today))
        ).count()

        # Financial Revenue Counters
        total_billed = all_invoices.aggregate(total=Sum('net_total_payable'))['total'] or Decimal('0.00')
        total_collected = all_invoices.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')
        total_receivables = max(Decimal('0.00'), total_billed - total_collected)

        overdue_invoices = all_invoices.filter(
            Q(status=Invoice.Status.OVERDUE) |
            (Q(status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID]) & Q(due_date__lt=today))
        )
        overdue_billed = overdue_invoices.aggregate(total=Sum('net_total_payable'))['total'] or Decimal('0.00')
        overdue_collected = overdue_invoices.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')
        total_overdue_amount = max(Decimal('0.00'), overdue_billed - overdue_collected)

        context['total_billed'] = total_billed
        context['total_collected'] = total_collected
        context['total_receivables'] = total_receivables
        context['total_overdue_amount'] = total_overdue_amount

        return context


class InvoiceDetailView(RoleRequiredMixin, DetailView):
    """
    Itemized A4-styled web dossier of Commercial Tax Invoice with excess hours breakdown,
    deposit deductions, payment history timeline, and WeasyPrint PDF download.
    """
    model = Invoice
    template_name = 'finance/invoice_detail.html'
    context_object_name = 'invoice'
    pk_url_kwarg = 'invoice_no'
    allowed_roles = (
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
        User.Role.RENTAL_OFFICER,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.object
        context['payments'] = invoice.payments.select_related('recorded_by').all()
        context['payment_form'] = PaymentForm(invoice=invoice)
        context['contract'] = invoice.contract
        context['customer'] = invoice.customer
        context['equipment'] = invoice.contract.equipment
        context['today'] = timezone.now().date()
        return context


class InvoicePDFDownloadView(RoleRequiredMixin, View):
    """
    Generates or streams the pixel-perfect A4 WeasyPrint PDF document for the invoice.
    """
    allowed_roles = (
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
        User.Role.RENTAL_OFFICER,
    )

    def get(self, request, invoice_no):
        invoice = get_object_or_404(Invoice, invoice_no=invoice_no)

        pdf_bytes = render_invoice_to_pdf(invoice, request=request)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        download = request.GET.get('download', '0') == '1'
        disposition = 'attachment' if download else 'inline'
        response['Content-Disposition'] = f'{disposition}; filename="Invoice-{invoice.invoice_no}.pdf"'
        return response


class GenerateInvoiceFromContractView(RoleRequiredMixin, FormView):
    """
    View for generating final settlement invoice for a given Rental Contract.
    """
    template_name = 'finance/generate_invoice.html'
    form_class = InvoiceGenerationForm
    allowed_roles = (
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_initial(self):
        initial = super().get_initial()
        contract_no = self.kwargs.get('contract_no')
        if contract_no:
            contract = get_object_or_404(RentalContract, contract_no=contract_no)
            initial['contract'] = contract
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract_no = self.kwargs.get('contract_no')
        if contract_no:
            context['contract'] = get_object_or_404(RentalContract, contract_no=contract_no)
        return context

    def form_valid(self, form):
        contract = form.cleaned_data['contract']
        due_date = form.cleaned_data.get('due_date')
        excess_hours_rate = form.cleaned_data.get('excess_hours_rate')
        damage_charges = form.cleaned_data.get('damage_charges') or Decimal('0.00')
        apply_deposit = form.cleaned_data.get('apply_security_deposit', True)

        try:
            invoice = generate_final_rental_invoice(
                contract_id=contract.contract_no,
                user=self.request.user,
                due_date=due_date,
                excess_hours_rate=excess_hours_rate,
                damage_charges=damage_charges,
                apply_deposit=apply_deposit,
            )
            messages.success(self.request, f"Tax Invoice '{invoice.invoice_no}' successfully generated for Contract '{contract.contract_no}'.")
            return redirect('finance:invoice_detail', invoice_no=invoice.invoice_no)
        except Exception as e:
            messages.error(self.request, f"Failed to generate invoice: {str(e)}")
            return self.form_invalid(form)


# ==============================================================================
# 2. PAYMENT ENTRY & TRANSACTION RECORDING VIEWS
# ==============================================================================

class PaymentCreateView(RoleRequiredMixin, View):
    """
    Fast payment posting dialog handling settlement entries, modal submissions,
    and automatic real-time invoice & customer balance updates.
    """
    allowed_roles = (
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get(self, request, invoice_no=None):
        invoice = None
        if invoice_no:
            invoice = get_object_or_404(Invoice, invoice_no=invoice_no)
        form = PaymentForm(invoice=invoice)
        return render(request, 'finance/payment_form.html', {'form': form, 'invoice': invoice})

    def post(self, request, invoice_no=None):
        invoice = None
        if invoice_no:
            invoice = get_object_or_404(Invoice, invoice_no=invoice_no)

        form = PaymentForm(request.POST, request.FILES, invoice=invoice)
        if form.is_valid():
            try:
                target_invoice = form.cleaned_data.get('invoice') or invoice
                if not target_invoice:
                    raise ValidationError("An invoice must be selected for rental payments.")

                payment = record_invoice_payment(
                    invoice_id=target_invoice.invoice_no,
                    payment_data=form.cleaned_data,
                    user=request.user
                )

                messages.success(
                    request,
                    f"Payment '{payment.payment_id}' of LKR {payment.amount:,.2f} recorded successfully for Invoice '{target_invoice.invoice_no}'."
                )

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': f"Payment {payment.payment_id} recorded successfully.",
                        'redirect_url': reverse('finance:invoice_detail', kwargs={'invoice_no': target_invoice.invoice_no})
                    })

                return redirect('finance:invoice_detail', invoice_no=target_invoice.invoice_no)

            except ValidationError as ve:
                messages.error(request, str(ve))
            except Exception as e:
                messages.error(request, f"Error posting payment: {str(e)}")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

        return render(request, 'finance/payment_form.html', {'form': form, 'invoice': invoice})


# ==============================================================================
# 3. SECURITY DEPOSIT ESCROW LEDGER VIEWS
# ==============================================================================

class SecurityDepositLedgerView(RoleRequiredMixin, ListView):
    """
    Escrow ledger tracking deposits held, deductions for damage/excess usage,
    and pending refunds linked to rental contracts.
    """
    model = SecurityDeposit
    template_name = 'finance/deposit_ledger.html'
    context_object_name = 'deposit_list'
    paginate_by = 25
    allowed_roles = (
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_queryset(self):
        queryset = SecurityDeposit.objects.select_related('contract', 'customer', 'contract__equipment')
        status_filter = self.request.GET.get('status', '').strip()
        search_query = self.request.GET.get('q', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(deposit_id__icontains=search_query) |
                Q(customer__company_name__icontains=search_query) |
                Q(contract__contract_no__icontains=search_query)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_deposits = SecurityDeposit.objects.all()

        context['selected_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')

        # KPI Metrics
        total_agreed = all_deposits.aggregate(total=Sum('deposit_amount'))['total'] or Decimal('0.00')
        total_deducted = all_deposits.aggregate(total=Sum('deducted_amount'))['total'] or Decimal('0.00')
        total_refunded = all_deposits.aggregate(total=Sum('refunded_amount'))['total'] or Decimal('0.00')
        total_held = max(Decimal('0.00'), total_agreed - total_deducted - total_refunded)

        context['total_deposits_count'] = all_deposits.count()
        context['total_agreed'] = total_agreed
        context['total_held'] = total_held
        context['total_deducted'] = total_deducted
        context['total_refunded'] = total_refunded
        context['pending_count'] = all_deposits.filter(status=SecurityDeposit.Status.PENDING).count()
        context['held_count'] = all_deposits.filter(status=SecurityDeposit.Status.HELD).count()

        return context


class DepositRefundView(RoleRequiredMixin, View):
    """
    Processes escrow deposit refund disbursement to customer.
    """
    allowed_roles = (
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get(self, request, deposit_id):
        deposit = get_object_or_404(SecurityDeposit, deposit_id=deposit_id)
        form = SecurityDepositRefundForm(deposit=deposit)
        return render(request, 'finance/deposit_refund_modal.html', {'deposit': deposit, 'form': form})

    def post(self, request, deposit_id):
        deposit = get_object_or_404(SecurityDeposit, deposit_id=deposit_id)
        form = SecurityDepositRefundForm(deposit=deposit, data=request.POST)

        if form.is_valid():
            try:
                payment = process_deposit_refund(
                    deposit_id=deposit.deposit_id,
                    refund_data=form.cleaned_data,
                    user=request.user
                )
                messages.success(
                    request,
                    f"Deposit refund of LKR {payment.amount:,.2f} successfully disbursed (Transaction ID: {payment.payment_id})."
                )
                return redirect('finance:deposit_ledger')
            except ValidationError as ve:
                messages.error(request, str(ve))
            except Exception as e:
                messages.error(request, f"Error processing refund: {str(e)}")

        return render(request, 'finance/deposit_refund_modal.html', {'deposit': deposit, 'form': form})
