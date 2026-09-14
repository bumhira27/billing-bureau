import threading

_thread_locals = threading.local()

def get_current_practice():
    return getattr(_thread_locals, 'practice', None)

def set_current_practice(practice):
    _thread_locals.practice = practice

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'provider_profile'):
            # This is a naive assignment for phase 1. Realistically, users might have multiple practices or practice is determined by subdomain/session.
            set_current_practice(request.user.provider_profile.practice)
        else:
            set_current_practice(None)
            
        response = self.get_response(request)
        
        # Clean up
        set_current_practice(None)
        
        return response
