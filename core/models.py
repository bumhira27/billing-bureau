from django.db import models
from django.contrib.auth.models import User

class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created_at`` and ``updated_at`` fields, along with an optional
    ``created_by`` user relationship.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        verbose_name="Created By",
        related_name="%(app_label)s_%(class)s_created"
    )

    class Meta:
        abstract = True
