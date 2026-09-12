from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class IdempotencyRecord(models.Model):
    idempotency_key = models.CharField(max_length=255, db_index=True)
    scope = models.CharField(max_length=100, default='default')
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    endpoint = models.CharField(max_length=255)
    request_hash = models.CharField(max_length=64, blank=True)
    status_code = models.IntegerField()
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('idempotency_key', 'scope')
        indexes = [
            models.Index(fields=['idempotency_key', 'scope']),
        ]
        verbose_name = 'Idempotency Record'
        verbose_name_plural = 'Idempotency Records'

    def __str__(self):
        return f"{self.idempotency_key} ({self.endpoint} -> {self.status_code})"
