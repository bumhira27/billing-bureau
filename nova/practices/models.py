from django.db import models
from core.models import TimeStampedModel, PublicIdModel, TenantModel
from django.conf import settings

class Practice(TimeStampedModel, PublicIdModel):
    name = models.CharField(max_length=255)
    practice_number = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Provider(TimeStampedModel, PublicIdModel, TenantModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='provider_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100, blank=True)
    bhf_number = models.CharField(max_length=100, blank=True, help_text="BHF Practice Number")
    hpcsa_number = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name}"

class Room(TimeStampedModel, PublicIdModel, TenantModel):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class AppointmentType(TimeStampedModel, PublicIdModel, TenantModel):
    name = models.CharField(max_length=100)
    default_duration_minutes = models.PositiveIntegerField(default=15)
    color_hex = models.CharField(max_length=7, default="#3b82f6")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class WorkingHours(TimeStampedModel, PublicIdModel, TenantModel):
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='working_hours', null=True, blank=True)
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.get_day_of_week_display()} ({self.start_time} - {self.end_time})"
