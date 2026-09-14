from django.db import models
from core.models import TimeStampedModel, PublicIdModel, TenantModel

class Appointment(TimeStampedModel, PublicIdModel, TenantModel):
    STATUS_CHOICES = [
        ('booked', 'Booked'),
        ('confirmed', 'Confirmed'),
        ('arrived', 'Arrived'),
        ('in_consultation', 'In Consultation'),
        ('ready_for_checkout', 'Ready for Checkout'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='appointments')
    provider = models.ForeignKey('practices.Provider', on_delete=models.CASCADE, related_name='appointments')
    room = models.ForeignKey('practices.Room', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    appointment_type = models.ForeignKey('practices.AppointmentType', on_delete=models.SET_NULL, null=True, blank=True)
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')
    
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.patient} with {self.provider} at {self.start_time}"

class WaitlistEntry(TimeStampedModel, PublicIdModel, TenantModel):
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='waitlist_entries')
    preferred_provider = models.ForeignKey('practices.Provider', on_delete=models.SET_NULL, null=True, blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    urgency = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Waitlist: {self.patient}"
