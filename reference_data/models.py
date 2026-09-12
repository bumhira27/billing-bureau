from django.db import models
from core.models import TimeStampedModel

class ICD10Code(TimeStampedModel):
    """
    Model representing an ICD-10 diagnosis code.
    """
    code = models.CharField(max_length=10, unique=True, db_index=True)
    description = models.CharField(max_length=500)
    category = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'ICD-10 Code'

    def __str__(self):
        return f"{self.code} - {self.description}"

class TariffCode(TimeStampedModel):
    """
    Model representing a medical tariff code used for billing procedures and services.
    """
    code = models.CharField(max_length=20, unique=True, db_index=True)
    description = models.CharField(max_length=500)
    category = models.CharField(max_length=255, blank=True)
    default_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Tariff Code'

    def __str__(self):
        return f"{self.code} - {self.description}"

class RejectionCode(TimeStampedModel):
    """
    Model representing medical scheme rejection codes and recommended actions.
    """
    CATEGORY_CHOICES = [
        ('administrative', 'Administrative'),
        ('clinical', 'Clinical'),
        ('pmb', 'PMB Related'),
        ('financial', 'Financial'),
        ('other', 'Other')
    ]

    code = models.CharField(max_length=20, unique=True, db_index=True)
    description = models.CharField(max_length=500)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    suggested_action = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Rejection Code'

    def __str__(self):
        return f"{self.code} - {self.description}"
