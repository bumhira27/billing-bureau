from django.db import models
from core.models import TimeStampedModel


class MedicalAidPortalCredential(TimeStampedModel):
    ADMINISTRATOR_CHOICES = [
        ('discovery', 'Discovery Health Provider Portal'),
        ('medscheme', 'Medscheme / GEMS Provider Portal'),
        ('momentum', 'Momentum / Metropolitan Online'),
        ('universal', 'Universal Healthcare Portal'),
        ('simulator', 'Direct Portal Simulator (Dry-Run Test)'),
    ]

    administrator = models.CharField(
        max_length=50,
        choices=ADMINISTRATOR_CHOICES,
        unique=True,
        help_text="South African medical scheme administrator gateway"
    )
    username = models.CharField(
        max_length=100,
        help_text="Bureau master username or registered portal login ID"
    )
    password = models.CharField(
        max_length=255,
        help_text="Bureau portal login password"
    )
    portal_url = models.URLField(
        blank=True,
        help_text="Gateway URL for direct headless browser navigation"
    )
    bureau_bhf_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Bureau BHF accredited registration number (if applicable)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Enable for automated headless claim submission"
    )
    last_tested = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=100, blank=True, default="Untested")

    # Circuit Breaker Fields
    CIRCUIT_STATE_CHOICES = [
        ('closed', 'Healthy / Closed'),
        ('open', 'Tripped / Open'),
        ('half_open', 'Probing / Half-Open'),
    ]
    circuit_state = models.CharField(
        max_length=20,
        choices=CIRCUIT_STATE_CHOICES,
        default='closed',
        help_text="Circuit breaker status for gateway protection"
    )
    consecutive_failures = models.PositiveIntegerField(
        default=0,
        help_text="Consecutive submission or authentication failures"
    )
    failure_threshold = models.PositiveIntegerField(
        default=3,
        help_text="Failures before tripping the circuit breaker"
    )
    cooldown_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Duration in minutes to pause requests when tripped"
    )
    tripped_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when cooldown expires"
    )
    last_failure_reason = models.TextField(
        blank=True,
        help_text="Reason recorded on most recent gateway failure"
    )

    class Meta:
        ordering = ['administrator']
        verbose_name = 'Medical Aid Portal Credential'
        verbose_name_plural = 'Medical Aid Portal Credentials'

    def __str__(self):
        return f"{self.get_administrator_display()} ({self.username}) [{self.get_circuit_state_display()}]"

    def is_available(self):
        """Returns tuple (is_available: bool, reason: str)"""
        from django.utils import timezone
        if not self.is_active:
            return False, "Gateway credential is inactive."

        if self.circuit_state == 'open':
            if self.tripped_until and timezone.now() >= self.tripped_until:
                self.circuit_state = 'half_open'
                self.save(update_fields=['circuit_state'])
                return True, "Circuit half-open: probing gateway health."
            return False, f"Gateway circuit breaker tripped until {self.tripped_until.strftime('%H:%M:%S') if self.tripped_until else 'N/A'}. Error: {self.last_failure_reason}"

        return True, "Gateway available."

    def record_success(self):
        """Resets failures and closes the circuit on successful operation."""
        self.consecutive_failures = 0
        self.circuit_state = 'closed'
        self.tripped_until = None
        self.last_status = 'Authentication Verified'
        self.save(update_fields=['consecutive_failures', 'circuit_state', 'tripped_until', 'last_status'])

    def record_failure(self, reason: str):
        """Records a failure and trips the circuit if threshold is reached."""
        from django.utils import timezone
        from datetime import timedelta
        self.consecutive_failures += 1
        self.last_failure_reason = str(reason)
        self.last_tested = timezone.now()

        if self.consecutive_failures >= self.failure_threshold:
            self.circuit_state = 'open'
            self.tripped_until = timezone.now() + timedelta(minutes=self.cooldown_minutes)
            self.last_status = f"Circuit Tripped ({self.consecutive_failures} failures)"
        else:
            self.last_status = f"Failed ({self.consecutive_failures}/{self.failure_threshold})"

        self.save(update_fields=['consecutive_failures', 'last_failure_reason', 'last_tested', 'circuit_state', 'tripped_until', 'last_status'])

    def reset_circuit(self):
        """Manual administrative reset to healthy state."""
        self.consecutive_failures = 0
        self.circuit_state = 'closed'
        self.tripped_until = None
        self.last_failure_reason = ''
        self.last_status = 'Circuit Reset Manually'
        self.save(update_fields=['consecutive_failures', 'circuit_state', 'tripped_until', 'last_failure_reason', 'last_status'])
