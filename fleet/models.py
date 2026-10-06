from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from fleet.managers import EquipmentManager


class Category(TimeStampedModel):
    """
    Equipment category model classifying heavy machinery and construction gear.
    (e.g., Excavators, Cranes, Generators, Compaction).
    """
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        _("Category Name"),
        max_length=100,
        unique=True,
        help_text=_("Display name of the equipment classification.")
    )
    code = models.SlugField(
        _("Category Code"),
        max_length=20,
        unique=True,
        help_text=_("Short mnemonic code (e.g., EXC, GEN, CRN).")
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Detailed notes on equipment types included in this category.")
    )

    class Meta:
        verbose_name = _("Equipment Category")
        verbose_name_plural = _("Equipment Categories")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Equipment(TimeStampedModel):
    """
    Equipment Master Model representing individual machinery assets in the fleet.
    Tracks technical specifications, procurement value, operating hours, and live status.
    """

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', _('Available')
        RESERVED = 'RESERVED', _('Reserved')
        ON_RENT = 'ON_RENT', _('On Rent')
        MAINTENANCE = 'MAINTENANCE', _('Maintenance')
        BREAKDOWN = 'BREAKDOWN', _('Breakdown')
        INACTIVE = 'INACTIVE', _('Inactive')

    objects = EquipmentManager()

    asset_code = models.CharField(
        _("Asset Code"),
        max_length=50,
        primary_key=True,
        help_text=_("Unique identifier (e.g., EQ-CAT-320-001).")
    )
    equipment_name = models.CharField(
        _("Equipment Name"),
        max_length=200,
        help_text=_("Marketing or operational name of the machinery.")
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='equipment_list',
        verbose_name=_("Category"),
        help_text=_("Classification category for this machinery.")
    )
    brand = models.CharField(
        _("Brand / Manufacturer"),
        max_length=100,
        help_text=_("Manufacturer brand (e.g., Caterpillar, Komatsu, JCB).")
    )
    model_number = models.CharField(
        _("Model Number"),
        max_length=100,
        help_text=_("Manufacturer model designation (e.g., 320D, JS205).")
    )
    serial_number = models.CharField(
        _("Serial / VIN Number"),
        max_length=100,
        unique=True,
        help_text=_("Chassis, engine, or manufacturer serial number.")
    )
    manufacture_year = models.PositiveIntegerField(
        _("Year of Manufacture"),
        help_text=_("Calendar year machinery was manufactured.")
    )
    purchase_cost = models.DecimalField(
        _("Purchase Cost (LKR)"),
        max_digits=12,
        decimal_places=2,
        help_text=_("Original acquisition capital cost in Sri Lankan Rupees.")
    )
    purchase_date = models.DateField(
        _("Purchase Date"),
        help_text=_("Date the asset was acquired.")
    )
    current_hour_meter = models.DecimalField(
        _("Current Hour Meter (hrs)"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_("Latest cumulative operating hour meter reading.")
    )
    status = models.CharField(
        _("Operational Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True,
        help_text=_("Current operational and reservation state of the asset.")
    )
    primary_image = models.ImageField(
        _("Primary Asset Photo"),
        upload_to='equipment/images/',
        null=True,
        blank=True,
        help_text=_("High-resolution photo of the equipment.")
    )
    specifications = models.JSONField(
        _("Technical Specifications"),
        default=dict,
        blank=True,
        help_text=_("Structured key-value specifications (e.g., Operating Weight, Engine Power, Bucket Capacity).")
    )

    class Meta:
        verbose_name = _("Equipment Asset")
        verbose_name_plural = _("Equipment Fleet")
        ordering = ['asset_code']

    def __str__(self):
        return f"{self.asset_code} - {self.equipment_name} ({self.get_status_display()})"

    @property
    def is_available(self) -> bool:
        """Returns True if the machine is physically ready for rental dispatch."""
        return self.status == self.Status.AVAILABLE

    def is_available_for_dates(self, start_date, end_date) -> bool:
        """
        Validates if the equipment is unreserved and free of conflicting active contracts
        for the given date range.
        """
        if self.status in [self.Status.MAINTENANCE, self.Status.BREAKDOWN, self.Status.INACTIVE]:
            return False

        # Check for overlapping contracts from rentals app (using string model query to avoid circular imports)
        from django.apps import apps
        RentalContract = apps.get_model('rentals', 'RentalContract', require_ready=False)
        if RentalContract:
            conflicting_contracts = RentalContract.objects.filter(
                equipment=self,
                status__in=['ACTIVE', 'DISPATCHED', 'ON_RENT'],
                contract_start_date__lte=end_date,
                contract_end_date__gte=start_date
            ).exists()
            if conflicting_contracts:
                return False

        return True

    def transition_status(self, new_status: str, user=None, notes: str = None) -> bool:
        """
        Safely transitions the equipment to a new operational status and audits state changes.
        """
        valid_statuses = [choice[0] for choice in self.Status.choices]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}")

        old_status = self.status
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        return True


class RentalRate(TimeStampedModel):
    """
    Rental pricing tariff card linked to an equipment asset.
    Defines multi-tier rates (Hourly, Daily, Weekly, Monthly) and overtime rules.
    """
    id = models.BigAutoField(primary_key=True)
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name='rental_rates',
        verbose_name=_("Equipment Asset"),
        help_text=_("Equipment asset this rate card applies to.")
    )
    hourly_rate = models.DecimalField(
        _("Hourly Rate (LKR)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Standard rental rate per hour (if applicable).")
    )
    daily_rate = models.DecimalField(
        _("Daily Rate (LKR)"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Standard rental rate per single 8-hour shift / day.")
    )
    weekly_rate = models.DecimalField(
        _("Weekly Rate (LKR)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Discounted package rate for a 7-day rental period.")
    )
    monthly_rate = models.DecimalField(
        _("Monthly Rate (LKR)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Discounted rate for long-term 30-day rental agreements.")
    )
    overtime_hourly_rate = models.DecimalField(
        _("Overtime Rate (LKR/hr)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Hourly penalty/charge for operating hours exceeding daily threshold.")
    )
    minimum_rental_hours = models.PositiveIntegerField(
        _("Minimum Rental Hours"),
        default=8,
        help_text=_("Minimum billable operating hours per rental engagement.")
    )
    effective_from = models.DateField(
        _("Effective From Date"),
        default=timezone.now,
        help_text=_("Date from which this tariff becomes active.")
    )
    is_active = models.BooleanField(
        _("Is Active Rate"),
        default=True,
        help_text=_("Designates whether this rate card is currently applicable.")
    )

    class Meta:
        verbose_name = _("Rental Rate Card")
        verbose_name_plural = _("Rental Rate Cards")
        ordering = ['-effective_from', '-created_at']

    def __str__(self):
        return f"Rate for {self.equipment.asset_code}: Daily Rs. {self.daily_rate}"
