from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from users.models import User
from users.permissions import RoleRequiredMixin
from .models import Equipment, Category, RentalRate
from .forms import CategoryForm, EquipmentForm, RentalRateCreateFormSet, RentalRateUpdateFormSet


# ==============================================================================
# 1. EQUIPMENT CATEGORY VIEWS
# ==============================================================================

class CategoryListView(RoleRequiredMixin, ListView):
    """
    Fleet Category directory view providing server-side search, assigned asset counters,
    and DataTables integration.
    """
    model = Category
    template_name = 'fleet/category_list.html'
    context_object_name = 'category_list'
    paginate_by = 25
    allowed_roles = (
        User.Role.WORKSHOP_MANAGER,
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.ACCOUNTANT,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_queryset(self):
        queryset = Category.objects.annotate(equipment_count=Count('equipment_list')).order_by('name')
        search_query = self.request.GET.get('q', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['total_categories'] = Category.objects.count()
        context['total_equipment'] = Equipment.objects.count()
        return context


class CategoryCreateView(RoleRequiredMixin, CreateView):
    """View to register a new machinery Category classification."""
    model = Category
    form_class = CategoryForm
    template_name = 'fleet/category_form.html'
    success_url = reverse_lazy('fleet:category_list')
    allowed_roles = (
        User.Role.WORKSHOP_MANAGER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(
            self.request,
            f"Category '{self.object.name}' ({self.object.code}) created successfully."
        )
        return redirect('fleet:category_list')


class CategoryUpdateView(RoleRequiredMixin, UpdateView):
    """View to update an existing machinery Category."""
    model = Category
    form_class = CategoryForm
    template_name = 'fleet/category_form.html'
    slug_field = 'code'
    slug_url_kwarg = 'code'
    success_url = reverse_lazy('fleet:category_list')
    allowed_roles = (
        User.Role.WORKSHOP_MANAGER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(
            self.request,
            f"Category '{self.object.name}' ({self.object.code}) updated successfully."
        )
        return redirect('fleet:category_list')


# Alias for roadmap / interface compatibility
CategoryCreateUpdateView = CategoryCreateView


# ==============================================================================
# 2. EQUIPMENT MASTER ASSET VIEWS
# ==============================================================================

class EquipmentListView(RoleRequiredMixin, ListView):
    """
    Fleet list view providing server-side search, status badge counters,
    category filters, and DataTables integration.
    """
    model = Equipment
    template_name = 'fleet/equipment_list.html'
    context_object_name = 'equipment_list'
    paginate_by = 25
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.WORKSHOP_MANAGER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_queryset(self):
        queryset = Equipment.objects.select_related('category').prefetch_related('rental_rates')
        search_query = self.request.GET.get('q', '').strip()
        category_code = self.request.GET.get('category', '').strip()
        status_filter = self.request.GET.get('status', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(asset_code__icontains=search_query) |
                Q(equipment_name__icontains=search_query) |
                Q(serial_number__icontains=search_query) |
                Q(brand__icontains=search_query) |
                Q(model_number__icontains=search_query)
            )

        if category_code:
            queryset = queryset.filter(category__code=category_code)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_equipment = Equipment.objects.all()

        context['categories'] = Category.objects.all()
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')

        # KPI Counters for Fleet Dashboard
        context['total_fleet'] = all_equipment.count()
        context['available_count'] = all_equipment.filter(status=Equipment.Status.AVAILABLE).count()
        context['on_rent_count'] = all_equipment.filter(status=Equipment.Status.ON_RENT).count()
        context['reserved_count'] = all_equipment.filter(status=Equipment.Status.RESERVED).count()
        context['maintenance_count'] = all_equipment.filter(
            status__in=[Equipment.Status.MAINTENANCE, Equipment.Status.BREAKDOWN]
        ).count()

        return context


class EquipmentDetailView(RoleRequiredMixin, DetailView):
    """
    Detailed technical asset dossier displaying rate tariffs, specifications,
    hour meter telemetry, and active reservations.
    """
    model = Equipment
    template_name = 'fleet/equipment_detail.html'
    context_object_name = 'equipment'
    pk_url_kwarg = 'asset_code'
    allowed_roles = (
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.WORKSHOP_MANAGER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_rates'] = self.object.rental_rates.filter(is_active=True).order_by('-effective_from')
        context['all_rates'] = self.object.rental_rates.all().order_by('-effective_from')
        return context


class EquipmentCreateView(RoleRequiredMixin, CreateView):
    """View to register a new Equipment Asset along with its initial Rental Rate card."""
    model = Equipment
    form_class = EquipmentForm
    template_name = 'fleet/equipment_form.html'
    allowed_roles = (
        User.Role.WORKSHOP_MANAGER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['rate_formset'] = RentalRateCreateFormSet(self.request.POST, prefix='rates')
        else:
            context['rate_formset'] = RentalRateCreateFormSet(prefix='rates')
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        rate_formset = context['rate_formset']

        with transaction.atomic():
            self.object = form.save()
            if rate_formset.is_valid():
                rate_formset.instance = self.object
                rate_formset.save()
            else:
                return self.form_invalid(form)

        messages.success(self.request, f"Equipment '{self.object.asset_code}' successfully registered into Fleet Master.")
        return redirect('fleet:equipment_detail', asset_code=self.object.asset_code)


class EquipmentUpdateView(RoleRequiredMixin, UpdateView):
    """View to edit existing Equipment specifications, hour-meter, and rate tariffs."""
    model = Equipment
    form_class = EquipmentForm
    template_name = 'fleet/equipment_form.html'
    pk_url_kwarg = 'asset_code'
    allowed_roles = (
        User.Role.WORKSHOP_MANAGER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['rate_formset'] = RentalRateUpdateFormSet(self.request.POST, instance=self.object, prefix='rates')
        else:
            context['rate_formset'] = RentalRateUpdateFormSet(instance=self.object, prefix='rates')
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        rate_formset = context['rate_formset']

        with transaction.atomic():
            self.object = form.save()
            if rate_formset.is_valid():
                rate_formset.instance = self.object
                rate_formset.save()
            else:
                return self.form_invalid(form)

        messages.success(self.request, f"Equipment '{self.object.asset_code}' successfully updated.")
        return redirect('fleet:equipment_detail', asset_code=self.object.asset_code)


class EquipmentStatusUpdateView(RoleRequiredMixin, View):
    """AJAX/POST endpoint to rapidly transition equipment status (e.g. Maintenance/Breakdown)."""
    allowed_roles = (
        User.Role.WORKSHOP_MANAGER,
        User.Role.OPERATIONS_OFFICER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
    )

    def post(self, request, asset_code):
        equipment = get_object_or_404(Equipment, asset_code=asset_code)
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')

        try:
            equipment.transition_status(new_status, user=request.user, notes=notes)
            messages.success(request, f"Equipment status updated to {equipment.get_status_display()}.")
            return redirect('fleet:equipment_detail', asset_code=equipment.asset_code)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('fleet:equipment_detail', asset_code=equipment.asset_code)


class EquipmentAssetCodeGenerateAPIView(RoleRequiredMixin, View):
    """API endpoint to dynamically compute standard equipment asset code in real-time."""
    allowed_roles = (
        User.Role.WORKSHOP_MANAGER,
        User.Role.MANAGEMENT,
        User.Role.ADMINISTRATOR,
        User.Role.RENTAL_OFFICER,
        User.Role.OPERATIONS_OFFICER,
    )

    def get(self, request, *args, **kwargs):
        category_id = request.GET.get('category_id') or request.GET.get('category')
        brand = request.GET.get('brand', '').strip()
        model_number = request.GET.get('model_number', '').strip()

        if not category_id or not brand or not model_number:
            return JsonResponse({'success': False, 'message': 'Category, Brand, and Model are required.'}, status=400)

        generated_code = Equipment.generate_asset_code(
            category=category_id,
            brand=brand,
            model_number=model_number
        )

        return JsonResponse({
            'success': True,
            'asset_code': generated_code
        })

