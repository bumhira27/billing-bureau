from django.db import models
from core.models import TimeStampedModel
from practices.models import Practice
from django.core.exceptions import ValidationError

class BureauProfile(TimeStampedModel):
    name = models.CharField(max_length=255, default="Billing Bureau")
    logo = models.ImageField(upload_to="bureau_logos/", null=True, blank=True)
    default_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=2.00, help_text="Percentage, e.g., 2.00 for 2%")
    tax_number = models.CharField(max_length=50, blank=True)
    contact_details = models.TextField(blank=True)

    class Meta:
        verbose_name = "Bureau Profile"
        verbose_name_plural = "Bureau Profiles"

    def __str__(self):
        return self.name

    def clean(self):
        # Ensure only one instance exists
        if BureauProfile.objects.exists() and not self.pk:
            raise ValidationError("There can only be one BureauProfile instance.")

class PracticeInvoice(TimeStampedModel):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('paid', 'Paid'),
    ]

    practice = models.ForeignKey(Practice, on_delete=models.CASCADE, related_name='invoices')
    invoice_month = models.DateField(help_text="The month this invoice applies to (use the first day of the month)")
    total_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    class Meta:
        ordering = ['-invoice_month', 'practice']
        verbose_name = "Practice Invoice"
        verbose_name_plural = "Practice Invoices"

    def __str__(self):
        return f"{self.practice.name} - {self.invoice_month.strftime('%b %Y')} ({self.get_status_display()})"

class PracticeInvoiceLineItem(models.Model):
    invoice = models.ForeignKey(PracticeInvoice, on_delete=models.CASCADE, related_name='line_items')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']
        verbose_name = "Practice Invoice Line Item"
        verbose_name_plural = "Practice Invoice Line Items"

    def __str__(self):
        return f"{self.description} - {self.amount}"
