from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class User(AbstractUser):
    ROLE_CHOICES = [
        ('owner', 'Practice Owner / Admin'),
        ('clinician', 'Clinician'),
        ('receptionist', 'Receptionist / Front Desk'),
        ('billing', 'Billing User'),
    ]
    
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='receptionist')
    mfa_required = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
