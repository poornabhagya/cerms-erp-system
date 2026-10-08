from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView

from users.models import User
from users.permissions import RoleRequiredMixin
from fleet.models import Equipment, Category
from .api import CalendarEventsAPIView, EquipmentAvailabilityCheckAPIView
from .models import Customer, ProjectSite, Quotation, QuotationItem, RentalContract, RentalContractItem, DispatchReturn
from .forms import CustomerForm, ProjectSiteForm, QuotationForm, QuotationItemForm, QuotationItemFormSet, RentalContractForm, DispatchForm, ReturnForm
from .services import (
    validate_customer_credit_limit,
    convert_quotation_to_contract,
    process_equipment_dispatch,
    process_equipment_return
)


# ==============================================================================
# 1. CUSTOMER & PROJECT SITE VIEWS
# ==============================================================================

class CustomerListView(RoleRequiredMixin, ListView):
    """
    Customer registry view providing server-side search, status badge counters,
    credit standing indicators, and DataTables integration.
    """
    model = Customer
    template_name = 'rentals/customer_list.html'
    context_object_name = 'customer_list'
    paginate_by = 25
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_queryset(self):
        queryset = Customer.objects.annotate(sites_count=Count('project_sites'))
        search_query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(customer_code__icontains=search_query) |
                Q(company_name__icontains=search_query) |
                Q(contact_person__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(vat_tax_number__icontains=search_query)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_customers = Customer.objects.all()

        context['selected_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')

        # KPI Metrics for Customer Management
        context['total_customers'] = all_customers.count()
        context['active_customers'] = all_customers.filter(status=Customer.Status.ACTIVE).count()
        context['blocked_customers'] = all_customers.filter(status=Customer.Status.BLOCKED).count()
        
        aggregates = all_customers.aggregate(
            total_credit=Sum('credit_limit'),
            total_balance=Sum('current_outstanding_balance')
        )
        context['total_credit_extended'] = aggregates['total_credit'] or Decimal('0.00')
        context['total_outstanding_balance'] = aggregates['total_balance'] or Decimal('0.00')

        return context


class CustomerDetailView(RoleRequiredMixin, DetailView):
    """
    360-degree Customer Dossier displaying commercial profile, credit standing gauge,
    linked project sites list, and active rental history.
    """
    model = Customer
    template_name = 'rentals/customer_detail.html'
    context_object_name = 'customer'
    pk_url_kwarg = 'customer_code'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object

        # Linked Project Sites
        context['project_sites'] = customer.project_sites.all().order_by('-created_at')

        # Quotations & Contracts
        context['recent_quotations'] = customer.quotations.select_related('project_site').prefetch_related('items__equipment').order_by('-created_at')[:5]
        context['active_contracts'] = customer.contracts.select_related('equipment', 'project_site').order_by('-contract_start_date')[:5]

        # Credit utilization percentage
        if customer.credit_limit > Decimal('0.00'):
            utilization = (customer.current_outstanding_balance / customer.credit_limit) * 100
            context['credit_utilization_pct'] = min(100.0, float(utilization))
        else:
            context['credit_utilization_pct'] = 0.0

        return context


class CustomerCreateView(RoleRequiredMixin, CreateView):
    """View to register a new Customer enterprise record."""
    model = Customer
    form_class = CustomerForm
    template_name = 'rentals/customer_form.html'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Customer '{self.object.company_name}' ({self.object.customer_code}) registered successfully.")
        return redirect('rentals:customer_detail', customer_code=self.object.customer_code)


class CustomerUpdateView(RoleRequiredMixin, UpdateView):
    """View to update existing Customer commercial and financial parameters."""
    model = Customer
    form_class = CustomerForm
    template_name = 'rentals/customer_form.html'
    pk_url_kwarg = 'customer_code'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Customer '{self.object.company_name}' updated successfully.")
        return redirect('rentals:customer_detail', customer_code=self.object.customer_code)


class ProjectSiteListView(RoleRequiredMixin, ListView):
    """
    Project Site Directory view displaying active job sites, supervisor contacts, and GPS links.
    """
    model = ProjectSite
    template_name = 'rentals/site_list.html'
    context_object_name = 'site_list'
    paginate_by = 25
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_queryset(self):
        queryset = ProjectSite.objects.select_related('customer')
        search_query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '').strip()
        customer_filter = self.request.GET.get('customer', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(project_code__icontains=search_query) |
                Q(project_name__icontains=search_query) |
                Q(site_address__icontains=search_query) |
                Q(site_contact_person__icontains=search_query) |
                Q(site_contact_phone__icontains=search_query) |
                Q(customer__company_name__icontains=search_query)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if customer_filter:
            queryset = queryset.filter(customer__customer_code=customer_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_sites = ProjectSite.objects.all()

        context['customers'] = Customer.objects.filter(status=Customer.Status.ACTIVE).order_by('company_name')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_customer'] = self.request.GET.get('customer', '')
        context['search_query'] = self.request.GET.get('q', '')

        # KPI Metrics
        context['total_sites'] = all_sites.count()
        context['active_sites'] = all_sites.filter(status=ProjectSite.Status.ACTIVE).count()
        context['completed_sites'] = all_sites.filter(status=ProjectSite.Status.COMPLETED).count()

        return context


class ProjectSiteCreateView(RoleRequiredMixin, CreateView):
    """View to register a new Project Site under a customer organization."""
    model = ProjectSite
    form_class = ProjectSiteForm
    template_name = 'rentals/site_form.html'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_initial(self):
        initial = super().get_initial()
        customer_code = self.request.GET.get('customer', '').strip()
        if customer_code:
            try:
                initial['customer'] = Customer.objects.get(customer_code=customer_code)
            except Customer.DoesNotExist:
                pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Project Site '{self.object.project_name}' ({self.object.project_code}) registered successfully.")
        return redirect('rentals:site_list')


class ProjectSiteUpdateView(RoleRequiredMixin, UpdateView):
    """View to update an existing Project Site details."""
    model = ProjectSite
    form_class = ProjectSiteForm
    template_name = 'rentals/site_form.html'
    pk_url_kwarg = 'project_code'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Project Site '{self.object.project_name}' updated successfully.")
        return redirect('rentals:site_list')


class ProjectSiteCodeGenerateAPIView(RoleRequiredMixin, View):
    """
    Real-time API endpoint to calculate and preview standard project site code
    based on the selected customer.
    """
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get(self, request, *args, **kwargs):
        customer_code = request.GET.get('customer', '').strip()
        customer = None
        if customer_code:
            customer = Customer.objects.filter(customer_code=customer_code).first()

        generated_code = ProjectSite.generate_project_code(customer=customer)
        return JsonResponse({
            'success': True,
            'project_code': generated_code
        })


class ProjectSiteDeleteView(RoleRequiredMixin, View):
    """
    Administrator-only view to safely delete a ProjectSite record.
    Strictly restricted to ADMINISTRATOR role per docs/03_ROLES_AND_PERMISSIONS.md.
    Enforces relational integrity checks against active/historical Quotations and RentalContracts.
    """
    allowed_roles = (User.Role.ADMINISTRATOR,)

    def post(self, request, project_code):
        site = get_object_or_404(ProjectSite, project_code=project_code)

        # 1. Relational Integrity Check
        has_quotations = site.quotations.exists()
        has_contracts = site.contracts.exists()

        if has_quotations or has_contracts:
            messages.error(
                request,
                f"Cannot delete Project Site '{site.project_code}' ({site.project_name}) because it is linked to "
                f"existing commercial quotations or rental contracts. To archive it, update its operational status to 'COMPLETED' or 'INACTIVE' instead."
            )
            next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
            if next_url:
                return redirect(next_url)
            return redirect('rentals:site_list')

        # 2. Safe deletion
        site_code = site.project_code
        site_name = site.project_name
        site.delete()

        messages.success(
            request,
            f"Project Site '{site_code}' ({site_name}) was successfully deleted."
        )
        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('rentals:site_list')


# ==============================================================================
# 2. QUOTATION MANAGEMENT VIEWS
# ==============================================================================

class QuotationListView(RoleRequiredMixin, ListView):
    """
    Quotation register displaying commercial offers, lifecycle status tabs, and PDF export triggers.
    """
    model = Quotation
    template_name = 'rentals/quotation_list.html'
    context_object_name = 'quotation_list'
    paginate_by = 25
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_queryset(self):
        queryset = Quotation.objects.select_related('customer', 'project_site', 'approved_by').prefetch_related('items__equipment')
        search_query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(quotation_no__icontains=search_query) |
                Q(customer__company_name__icontains=search_query) |
                Q(items__equipment__asset_code__icontains=search_query) |
                Q(items__equipment__equipment_name__icontains=search_query)
            ).distinct()

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_quotations = Quotation.objects.all()

        context['selected_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')

        # KPI Counters
        context['total_quotations'] = all_quotations.count()
        context['draft_count'] = all_quotations.filter(status=Quotation.Status.DRAFT).count()
        context['pending_approval_count'] = all_quotations.filter(status=Quotation.Status.PENDING_INTERNAL_APPROVAL).count()
        context['approved_count'] = all_quotations.filter(status=Quotation.Status.APPROVED_BY_MANAGEMENT).count()
        context['accepted_count'] = all_quotations.filter(status=Quotation.Status.ACCEPTED).count()
        context['converted_count'] = all_quotations.filter(status=Quotation.Status.CONVERTED).count()

        return context


class QuotationDetailView(RoleRequiredMixin, DetailView):
    """
    Quotation dossier displaying itemized pricing, credit risk evaluation, and managerial approval controls.
    """
    model = Quotation
    template_name = 'rentals/quotation_detail.html'
    context_object_name = 'quotation'
    pk_url_kwarg = 'quotation_no'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quotation = self.object

        # Preloaded items
        context['items'] = quotation.items.select_related('equipment', 'equipment__category').all()

        # Real-time credit validation check
        context['credit_check'] = validate_customer_credit_limit(quotation.customer, quotation.grand_total_amount)
        context['can_approve'] = (self.request.user.role in [User.Role.MANAGEMENT, User.Role.ADMINISTRATOR] or self.request.user.is_superuser)
        context['can_convert'] = (quotation.status in [Quotation.Status.ACCEPTED, Quotation.Status.APPROVED_BY_MANAGEMENT]) and not hasattr(quotation, 'contract')
        context['has_contract'] = hasattr(quotation, 'contract')

        return context


class QuotationCreateView(RoleRequiredMixin, CreateView):
    """View to build and issue a new commercial Quotation with multi-asset line items."""
    model = Quotation
    form_class = QuotationForm
    template_name = 'rentals/quotation_form.html'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_initial(self):
        initial = super().get_initial()
        initial['quotation_no'] = Quotation.generate_quotation_no()
        initial['start_date'] = self.request.GET.get('start_date') or timezone.now().date()
        if self.request.GET.get('end_date'):
            initial['end_date'] = self.request.GET.get('end_date')
        if self.request.GET.get('customer'):
            try:
                initial['customer'] = Customer.objects.get(customer_code=self.request.GET.get('customer'))
            except Customer.DoesNotExist:
                pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        if self.request.POST:
            context['item_formset'] = QuotationItemFormSet(self.request.POST)
        else:
            initial_items = []
            if self.request.GET.get('equipment'):
                try:
                    eq = Equipment.objects.get(asset_code=self.request.GET.get('equipment'))
                    rate_card = eq.rental_rates.filter(is_active=True).first()
                    initial_items.append({
                        'equipment': eq,
                        'start_date': self.request.GET.get('start_date') or timezone.now().date(),
                        'end_date': self.request.GET.get('end_date') or None,
                        'rate_applied': rate_card.daily_rate if rate_card else Decimal('0.00'),
                        'rate_type': Quotation.RateType.DAILY,
                    })
                except Equipment.DoesNotExist:
                    pass
            if initial_items:
                context['item_formset'] = QuotationItemFormSet(initial=initial_items)
            else:
                context['item_formset'] = QuotationItemFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        if item_formset.is_valid():
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.save()
                item_formset.instance = self.object
                item_formset.save()

                # Re-calculate totals based on saved items
                totals = self.object.calculate_totals()
                self.object.subtotal_amount = totals['base_tariff']
                self.object.total_tax_amount = totals['tax_amount']
                self.object.grand_total_amount = totals['grand_total_amount']
                self.object.save(update_fields=['subtotal_amount', 'total_tax_amount', 'grand_total_amount', 'updated_at'])

            messages.success(self.request, f"Quotation '{self.object.quotation_no}' generated successfully.")
            return redirect('rentals:quotation_detail', quotation_no=self.object.quotation_no)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class QuotationUpdateView(RoleRequiredMixin, UpdateView):
    """View to modify an existing Quotation and its multi-asset line items."""
    model = Quotation
    form_class = QuotationForm
    template_name = 'rentals/quotation_form.html'
    pk_url_kwarg = 'quotation_no'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        if self.request.POST:
            context['item_formset'] = QuotationItemFormSet(self.request.POST, instance=self.object)
        else:
            context['item_formset'] = QuotationItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        if item_formset.is_valid():
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.save()
                item_formset.instance = self.object
                item_formset.save()

                # Re-calculate totals based on saved items
                totals = self.object.calculate_totals()
                self.object.subtotal_amount = totals['base_tariff']
                self.object.total_tax_amount = totals['tax_amount']
                self.object.grand_total_amount = totals['grand_total_amount']
                self.object.save(update_fields=['subtotal_amount', 'total_tax_amount', 'grand_total_amount', 'updated_at'])

            messages.success(self.request, f"Quotation '{self.object.quotation_no}' updated successfully.")
            return redirect('rentals:quotation_detail', quotation_no=self.object.quotation_no)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class QuotationStatusTransitionView(RoleRequiredMixin, View):
    """
    Handles lifecycle status transitions (Submit for Approval, Approve, Send, Accept, Reject, Convert).
    """
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def post(self, request, quotation_no):
        quotation = get_object_or_404(Quotation, quotation_no=quotation_no)
        action = request.POST.get('action')

        try:
            if action == 'submit_for_approval':
                quotation.status = Quotation.Status.PENDING_INTERNAL_APPROVAL
                quotation.save(update_fields=['status', 'updated_at'])
                messages.info(request, f"Quotation '{quotation.quotation_no}' submitted for management approval.")

            elif action == 'approve':
                if request.user.role not in [User.Role.MANAGEMENT, User.Role.ADMINISTRATOR] and not request.user.is_superuser:
                    messages.error(request, "Only Management or Administrators can approve commercial quotations.")
                    return redirect('rentals:quotation_detail', quotation_no=quotation.quotation_no)
                quotation.status = Quotation.Status.APPROVED_BY_MANAGEMENT
                quotation.approved_by = request.user
                quotation.approval_date = timezone.now()
                quotation.save(update_fields=['status', 'approved_by', 'approval_date', 'updated_at'])
                messages.success(request, f"Quotation '{quotation.quotation_no}' approved by Management.")

            elif action == 'send_to_customer':
                quotation.status = Quotation.Status.SENT_TO_CUSTOMER
                quotation.save(update_fields=['status', 'updated_at'])
                messages.success(request, f"Quotation '{quotation.quotation_no}' marked as Sent to Customer.")

            elif action == 'mark_accepted':
                quotation.status = Quotation.Status.ACCEPTED
                quotation.save(update_fields=['status', 'updated_at'])
                messages.success(request, f"Quotation '{quotation.quotation_no}' accepted by Customer.")

            elif action == 'reject':
                quotation.status = Quotation.Status.REJECTED
                quotation.save(update_fields=['status', 'updated_at'])
                messages.warning(request, f"Quotation '{quotation.quotation_no}' marked as Rejected.")

            elif action == 'convert_to_contract':
                billing_cycle = request.POST.get('billing_cycle', 'MONTHLY')
                contract = convert_quotation_to_contract(quotation.quotation_no, user=request.user, billing_cycle=billing_cycle)
                messages.success(request, f"Quotation '{quotation.quotation_no}' successfully converted to Contract '{contract.contract_no}'. Equipment reserved.")
                return redirect('rentals:contract_detail', contract_no=contract.contract_no)

        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('rentals:quotation_detail', quotation_no=quotation.quotation_no)


class QuotationDeleteView(RoleRequiredMixin, View):
    """
    Administrator-only view to safely delete an unwanted/unconverted Quotation record.
    Strictly restricted to ADMINISTRATOR role per docs/03_ROLES_AND_PERMISSIONS.md.
    Enforces relational integrity checks: prevents deletion of quotations converted to binding RentalContracts.
    """
    allowed_roles = (User.Role.ADMINISTRATOR,)

    def post(self, request, quotation_no):
        quotation = get_object_or_404(Quotation, quotation_no=quotation_no)

        # Relational Integrity Check: converted contract exists?
        has_contract = hasattr(quotation, 'contract') or quotation.status == Quotation.Status.CONVERTED

        if has_contract:
            contract_ref = quotation.contract.contract_no if hasattr(quotation, 'contract') else "Binding Contract"
            messages.error(
                request,
                f"Cannot delete Quotation '{quotation.quotation_no}' because it has already been converted into a "
                f"legally binding Rental Contract ({contract_ref})."
            )
            next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
            if next_url:
                return redirect(next_url)
            return redirect('rentals:quotation_detail', quotation_no=quotation.quotation_no)

        # Safe deletion
        quote_no = quotation.quotation_no
        customer_name = quotation.customer.company_name
        quotation.delete()

        messages.success(
            request,
            f"Quotation '{quote_no}' ({customer_name}) was successfully deleted."
        )
        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('rentals:quotation_list')


# ==============================================================================
# 3. RENTAL CONTRACT & LOGISTICS (DISPATCH / RETURN) VIEWS
# ==============================================================================

class RentalContractListView(RoleRequiredMixin, ListView):
    """
    Active rental contract registry displaying machine assignments, billing cycles, and return dates.
    """
    model = RentalContract
    template_name = 'rentals/contract_list.html'
    context_object_name = 'contract_list'
    paginate_by = 25
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.WORKSHOP_MANAGER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_queryset(self):
        queryset = RentalContract.objects.select_related('customer', 'project_site', 'equipment', 'quotation')
        search_query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(contract_no__icontains=search_query) |
                Q(customer__company_name__icontains=search_query) |
                Q(equipment__asset_code__icontains=search_query) |
                Q(equipment__equipment_name__icontains=search_query) |
                Q(project_site__project_name__icontains=search_query)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_contracts = RentalContract.objects.all()

        context['selected_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')

        # KPI Counters
        context['total_contracts'] = all_contracts.count()
        context['active_count'] = all_contracts.filter(status=RentalContract.Status.ACTIVE).count()
        context['on_rent_count'] = all_contracts.filter(status=RentalContract.Status.ON_RENT).count()
        context['returned_count'] = all_contracts.filter(status=RentalContract.Status.RETURNED).count()
        context['closed_count'] = all_contracts.filter(status=RentalContract.Status.CLOSED).count()

        return context


class RentalContractDetailView(RoleRequiredMixin, DetailView):
    """
    Rental contract dashboard displaying agreed rates, physical handover history, and return actions.
    """
    model = RentalContract
    template_name = 'rentals/contract_detail.html'
    context_object_name = 'contract'
    pk_url_kwarg = 'contract_no'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.WORKSHOP_MANAGER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.object

        context['dispatch_logs'] = contract.dispatch_returns.select_related('dispatch_officer', 'return_officer').order_by('-dispatch_datetime')
        context['active_dispatch'] = contract.dispatch_returns.filter(return_datetime__isnull=True).first()
        context['can_dispatch'] = contract.status in [RentalContract.Status.ACTIVE, RentalContract.Status.DISPATCHED]
        context['can_return'] = contract.status == RentalContract.Status.ON_RENT and context['active_dispatch'] is not None

        return context


class DispatchCreateView(RoleRequiredMixin, CreateView):
    """
    View for yard officers to log equipment mobilization departure and initial telemetry.
    """
    model = DispatchReturn
    form_class = DispatchForm
    template_name = 'rentals/dispatch_form.html'
    allowed_roles = (
        User.Role.OPERATIONS_OFFICER,
        User.Role.WORKSHOP_MANAGER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_initial(self):
        initial = super().get_initial()
        contract_no = self.kwargs.get('contract_no')
        if contract_no:
            contract = get_object_or_404(RentalContract, contract_no=contract_no)
            initial['contract'] = contract
            initial['equipment'] = contract.equipment
            initial['dispatch_hour_meter'] = contract.equipment.current_hour_meter
            initial['dispatch_fuel_level'] = Decimal('100.00')
            initial['dispatch_datetime'] = timezone.now().strftime('%Y-%m-%dT%H:%M')

            current_year = timezone.now().year
            count = DispatchReturn.objects.filter(transaction_id__startswith=f"TRX-{current_year}-").count() + 1
            initial['transaction_id'] = f"TRX-{current_year}-{count:04d}"

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract_no = self.kwargs.get('contract_no')
        context['contract'] = get_object_or_404(RentalContract, contract_no=contract_no)
        return context

    def form_valid(self, form):
        contract_no = self.kwargs.get('contract_no')
        contract = get_object_or_404(RentalContract, contract_no=contract_no)

        dispatch_data = {
            'dispatch_datetime': form.cleaned_data['dispatch_datetime'],
            'dispatch_hour_meter': form.cleaned_data['dispatch_hour_meter'],
            'dispatch_fuel_level': form.cleaned_data['dispatch_fuel_level'],
            'dispatch_checklist': form.cleaned_data['dispatch_checklist'],
        }

        try:
            record = process_equipment_dispatch(contract.contract_no, dispatch_data, user=self.request.user)
            messages.success(self.request, f"Equipment '{contract.equipment.asset_code}' successfully dispatched under Transaction {record.transaction_id}.")
            return redirect('rentals:contract_detail', contract_no=contract.contract_no)
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


class ReturnCreateView(RoleRequiredMixin, UpdateView):
    """
    View for yard officers to log equipment return check-in, compute excess hours, and evaluate damages.
    """
    model = DispatchReturn
    form_class = ReturnForm
    template_name = 'rentals/return_form.html'
    pk_url_kwarg = 'transaction_id'
    allowed_roles = (
        User.Role.OPERATIONS_OFFICER,
        User.Role.WORKSHOP_MANAGER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_initial(self):
        initial = super().get_initial()
        initial['return_datetime'] = timezone.now().strftime('%Y-%m-%dT%H:%M')
        initial['return_hour_meter'] = self.object.equipment.current_hour_meter
        initial['return_fuel_level'] = Decimal('100.00')
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dispatch_record'] = self.object
        context['contract'] = self.object.contract
        return context

    def form_valid(self, form):
        return_data = {
            'return_datetime': form.cleaned_data['return_datetime'],
            'return_hour_meter': form.cleaned_data['return_hour_meter'],
            'return_fuel_level': form.cleaned_data['return_fuel_level'],
            'damage_reported': form.cleaned_data['damage_reported'],
            'damage_notes': form.cleaned_data['damage_notes'],
            'return_checklist': form.cleaned_data['return_checklist'],
        }

        try:
            record = process_equipment_return(self.object.transaction_id, return_data, user=self.request.user)
            messages.success(
                self.request,
                f"Equipment '{record.equipment.asset_code}' returned successfully. "
                f"Total hours: {record.hours_operated} hrs (Excess: {record.excess_hours_calculated} hrs)."
            )
            return redirect('rentals:contract_detail', contract_no=record.contract.contract_no)
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


# ==============================================================================
# 5. AVAILABILITY CALENDAR & VISUAL SCHEDULING
# ==============================================================================

class AvailabilityCalendarView(RoleRequiredMixin, TemplateView):
    """
    Interactive FullCalendar & timeline visualizer mapping fleet availability,
    contract on-rent engagements, accepted quotation reservations, and maintenance downtime.
    Reference: docs/23_PHASE_1_ROADMAP.md (Step 6.2)
    """
    template_name = 'rentals/calendar.html'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.WORKSHOP_MANAGER,
        User.Role.ACCOUNTANT,
        User.Role.STOREKEEPER,
        User.Role.FIELD_OFFICER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_equipment = Equipment.objects.select_related('category').prefetch_related('rental_rates').all()

        context['categories'] = Category.objects.all().order_by('name')
        context['equipment_list'] = all_equipment.order_by('asset_code')
        context['customers'] = Customer.objects.filter(status=Customer.Status.ACTIVE).order_by('company_name')

        # KPI Fleet Counters
        context['total_equipment'] = all_equipment.count()
        context['available_count'] = all_equipment.filter(status=Equipment.Status.AVAILABLE).count()
        context['on_rent_count'] = all_equipment.filter(status=Equipment.Status.ON_RENT).count()
        context['reserved_count'] = all_equipment.filter(status=Equipment.Status.RESERVED).count()
        context['maintenance_count'] = all_equipment.filter(
            status__in=[Equipment.Status.MAINTENANCE, Equipment.Status.BREAKDOWN]
        ).count()

        return context
