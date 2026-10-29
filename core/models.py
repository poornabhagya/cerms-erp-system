from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.middleware import get_current_user


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created_at``, ``updated_at``, and automated ``created_by`` audit fields.
    """
    created_at = models.DateTimeField(
        _("Created At"),
        auto_now_add=True,
        db_index=True,
        help_text=_("Timestamp when this record was created.")
    )
    updated_at = models.DateTimeField(
        _("Updated At"),
        auto_now=True,
        help_text=_("Timestamp when this record was last modified.")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created_by",
        verbose_name=_("Created By"),
        help_text=_("User who created this record.")
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """
        Automatically populate created_by with the authenticated user from the active
        request context when the record is initially created, unless explicitly supplied.
        """
        if self._state.adding and not getattr(self, 'created_by_id', None):
            user = get_current_user()
            if user and getattr(user, 'is_authenticated', False):
                self.created_by = user
                update_fields = kwargs.get('update_fields')
                if update_fields is not None:
                    kwargs['update_fields'] = set(update_fields) | {'created_by'}
        super().save(*args, **kwargs)
