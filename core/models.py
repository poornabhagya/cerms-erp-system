from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created_at`` and ``updated_at`` fields.
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

    class Meta:
        abstract = True
        ordering = ['-created_at']
