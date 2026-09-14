from django.db import models
import uuid

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class PublicIdModel(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        abstract = True

class TenantManager(models.Manager):
    def get_queryset(self):
        from core.middleware import get_current_practice
        practice = get_current_practice()
        if practice:
            return super().get_queryset().filter(practice=practice)
        return super().get_queryset()

class TenantModel(models.Model):
    practice = models.ForeignKey('practices.Practice', on_delete=models.CASCADE, related_name="%(class)ss")

    objects = TenantManager()

    class Meta:
        abstract = True

class AuditEvent(TimeStampedModel, PublicIdModel):
    # Not inheriting from TenantModel directly because some events might not have a practice context initially
    practice = models.ForeignKey('practices.Practice', on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")
    action = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} {self.action} on {self.resource_type} at {self.created_at}"
