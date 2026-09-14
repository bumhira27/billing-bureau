from django.db import models
from core.models import TimeStampedModel, PublicIdModel, TenantModel

class OutboxEvent(TimeStampedModel, PublicIdModel, TenantModel):
    EVENT_TYPES = [
        ('claim_submit', 'Submit Claim'),
        ('claim_resubmit', 'Resubmit Claim'),
    ]

    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    payload = models.JSONField()
    idempotency_key = models.CharField(max_length=100, unique=True)
    
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['created_at']

class WebhookLog(TimeStampedModel):
    """
    Records incoming webhooks from Billing Bureau
    """
    event_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    is_processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
