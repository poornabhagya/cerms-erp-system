from decimal import Decimal
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from users.models import User
from users.permissions import RoleRequiredMixin
from .models import Customer, ProjectSite
from .forms import CustomerForm, ProjectSiteForm


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
