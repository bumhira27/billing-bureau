import re
from patients.models import Patient, PHIReadAudit

class PHIReadLoggerMiddleware:
    """
    Middleware to log read access to patient PHI.
    Intercepts responses and checks if a specific patient was accessed.
    This is a simplified approach; in production, this would be tied to specific API endpoints or View mixins.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Naive detection of patient detail views for demonstration purposes.
        # e.g., /patients/1/, /api/v1/patients/1/
        match = re.search(r'/patients/(\d+)/', request.path)
        if match and request.method == 'GET':
            patient_id = match.group(1)
            try:
                patient = Patient.objects.get(pk=patient_id)
                PHIReadAudit.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    patient=patient,
                    endpoint=request.path,
                    ip_address=self.get_client_ip(request)
                )
            except Patient.DoesNotExist:
                pass

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
