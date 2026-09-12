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

from django.shortcuts import redirect
from django.urls import reverse

class EnforceBureauAdminMFAMiddleware:
    """
    Ensures that users in the BureauAdmin group have verified via MFA.
    If they are not verified, forces them to the 2FA setup or verification page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_verified():
            if request.user.is_superuser or request.user.groups.filter(name="BureauAdmin").exists():
                # Allow access to auth/setup pages
                allowed_paths = [
                    reverse("two_factor:setup"),
                    reverse("two_factor:login"),
                    reverse("logout"),
                ]
                
                # Check if path is a two_factor view (e.g. setup, qr code)
                if not any(request.path.startswith(p) for p in allowed_paths) and not request.path.startswith("/account/two_factor/"):
                    # Check if they have a device
                    from django_otp import user_has_device
                    if not user_has_device(request.user):
                        return redirect("two_factor:setup")
                    else:
                        # They have a device but are not verified. They need to login again via two-factor
                        from django.contrib.auth import logout
                        logout(request)
                        return redirect("two_factor:login")

        return self.get_response(request)
