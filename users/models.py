from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from .managers import CustomUserManager


class User(AbstractUser, TimeStampedModel):
    """
    Custom User model for CERMS, enforcing Role-Based Access Control (RBAC)
    across the 8 distinct organizational roles.
    """

    class Role(models.TextChoices):
        ADMINISTRATOR = 'ADMINISTRATOR', _('Administrator')
        MANAGEMENT = 'MANAGEMENT', _('Management')
        RENTAL_OFFICER = 'RENTAL_OFFICER', _('Rental Officer')
        OPERATIONS_OFFICER = 'OPERATIONS_OFFICER', _('Operations Officer')
        WORKSHOP_MANAGER = 'WORKSHOP_MANAGER', _('Workshop Manager')
        ACCOUNTANT = 'ACCOUNTANT', _('Accountant')
        STOREKEEPER = 'STOREKEEPER', _('Storekeeper')
        FIELD_OFFICER = 'FIELD_OFFICER', _('Field Officer')

    id = models.BigAutoField(
        primary_key=True,
        help_text=_("Unique integer ID for the user.")
    )
    email = models.EmailField(
        _("Email Address"),
        unique=True,
        db_index=True,
        error_messages={
            'unique': _("A user with that email already exists."),
        },
        help_text=_("Primary corporate email address.")
    )
    role = models.CharField(
        _("System Role"),
        max_length=30,
        choices=Role.choices,
        default=Role.RENTAL_OFFICER,
        db_index=True,
        help_text=_("Designated operational role determining system permissions.")
    )
    phone_number = models.CharField(
        _("Phone Number"),
        max_length=20,
        blank=True,
        help_text=_("Contact phone or mobile number.")
    )
    employee_id = models.CharField(
        _("Employee ID"),
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Unique organizational employee/payroll code.")
    )

    objects = CustomUserManager()

    REQUIRED_FIELDS = ['email', 'role']

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ['-date_joined']

    def __str__(self):
        full_name = self.get_full_name()
        display = full_name if full_name else self.username
        return f"{display} ({self.get_role_display()})"

    @property
    def is_administrator(self) -> bool:
        """Returns True if the user has the Administrator role or is a superuser."""
        return self.role == self.Role.ADMINISTRATOR or self.is_superuser

    @property
    def is_management(self) -> bool:
        """Returns True if the user belongs to Executive Management."""
        return self.role == self.Role.MANAGEMENT or self.is_administrator

    @property
    def is_rental_officer(self) -> bool:
        """Returns True if the user is a Rental Officer."""
        return self.role == self.Role.RENTAL_OFFICER

    @property
    def is_operations_officer(self) -> bool:
        """Returns True if the user is an Operations Officer."""
        return self.role == self.Role.OPERATIONS_OFFICER

    @property
    def is_workshop_manager(self) -> bool:
        """Returns True if the user is a Workshop Manager."""
        return self.role == self.Role.WORKSHOP_MANAGER

    @property
    def is_accountant(self) -> bool:
        """Returns True if the user has the Accountant role."""
        return self.role == self.Role.ACCOUNTANT

    @property
    def is_storekeeper(self) -> bool:
        """Returns True if the user has the Storekeeper role."""
        return self.role == self.Role.STOREKEEPER

    @property
    def is_field_officer(self) -> bool:
        """Returns True if the user is a Field Officer."""
        return self.role == self.Role.FIELD_OFFICER
