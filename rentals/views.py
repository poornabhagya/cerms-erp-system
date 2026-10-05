from decimal import Decimal
from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from users.models import User
from users.permissions import RoleRequiredMixin
from .models import Customer, ProjectSite
from .forms import CustomerForm, ProjectSiteForm


# ============================================================================
# 1. CUSTOMER MASTER VIEWS
# ============================================================================

class CustomerListView(RoleRequiredMixin, ListView):
    """
    Customer Master directory providing server-side search, credit tracking,
    commercial status filters, and DataTables integration.
    """
    model = Customer
    template_name = 'rentals/customer_list.html'
    context_object_name = 'customer_list'
    paginate_by = 25
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_queryset(self):
        queryset = Customer.objects.prefetch_related('project_sites')
        search_query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(customer_code__icontains=search_query) |
                Q(company_name__icontains=search_query) |
                Q(contact_person__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(vat_tax_number__icontains=search_query)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_customers = Customer.objects.all()

        context['search_query'] = self.request.GET.get('q', '')
        context['selected_status'] = self.request.GET.get('status', '')

        # KPI Metrics for Customers
        context['total_customers'] = all_customers.count()
        context['active_count'] = all_customers.filter(status=Customer.Status.ACTIVE).count()
        context['blocked_count'] = all_customers.filter(status=Customer.Status.BLOCKED).count()
        
        receivables_sum = all_customers.aggregate(total=Sum('current_outstanding_balance'))['total']
        context['total_receivables'] = receivables_sum if receivables_sum else Decimal('0.00')

        return context


class CustomerDetailView(RoleRequiredMixin, DetailView):
    """
    360-degree commercial customer dossier displaying credit telemetry,
    registered project sites, and commercial history.
    """
    model = Customer
    template_name = 'rentals/customer_detail.html'
    context_object_name = 'customer'
    pk_url_kwarg = 'customer_code'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer: Customer = self.object
        context['project_sites'] = customer.project_sites.all().order_by('-created_at')

        # Credit utilization percentage calculation
        if customer.credit_limit > Decimal('0.00'):
            utilization = (customer.current_outstanding_balance / customer.credit_limit) * Decimal('100.0')
            context['credit_utilization_pct'] = min(Decimal('100.0'), round(utilization, 1))
        else:
            context['credit_utilization_pct'] = Decimal('0.0')

        return context


class CustomerCreateView(RoleRequiredMixin, CreateView):
    """View to register a new corporate Customer into the system."""
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
        messages.success(self.request, f"Customer '{self.object.company_name}' ({self.object.customer_code}) successfully registered.")
        return redirect('rentals:customer_detail', customer_code=self.object.customer_code)


class CustomerUpdateView(RoleRequiredMixin, UpdateView):
    """View to update customer profile, billing address, or credit limit."""
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
        messages.success(self.request, f"Customer '{self.object.company_name}' details updated successfully.")
        return redirect('rentals:customer_detail', customer_code=self.object.customer_code)


# ============================================================================
# 2. PROJECT SITE VIEWS
# ============================================================================

class ProjectSiteCreateView(RoleRequiredMixin, CreateView):
    """View to register a new Project Site for a customer."""
    model = ProjectSite
    form_class = ProjectSiteForm
    template_name = 'rentals/projectsite_form.html'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_initial(self):
        initial = super().get_initial()
        customer_code = self.request.GET.get('customer')
        if customer_code:
            customer = Customer.objects.filter(customer_code=customer_code).first()
            if customer:
                initial['customer'] = customer
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Project Site '{self.object.project_name}' registered successfully.")
        return redirect('rentals:customer_detail', customer_code=self.object.customer.customer_code)


class ProjectSiteUpdateView(RoleRequiredMixin, UpdateView):
    """View to modify an existing Project Construction Site destination."""
    model = ProjectSite
    form_class = ProjectSiteForm
    template_name = 'rentals/projectsite_form.html'
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
        return redirect('rentals:customer_detail', customer_code=self.object.customer.customer_code)
