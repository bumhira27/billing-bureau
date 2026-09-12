import functools
import json
import hashlib
from django.http import JsonResponse, HttpResponse
from .models import IdempotencyRecord
from .utils import problem_details


def idempotent_endpoint(scope=None):
    """
    Decorator that enforces Idempotency-Key on state-modifying requests.
    If an identical key was previously processed, returns the exact cached response.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.method not in ['POST', 'PUT', 'PATCH']:
                return view_func(request, *args, **kwargs)

            idempotency_key = request.META.get('HTTP_IDEMPOTENCY_KEY')
            if not idempotency_key or not idempotency_key.strip():
                return problem_details(
                    status=400,
                    title="Missing Idempotency-Key",
                    detail="An 'Idempotency-Key' HTTP header is required for this financial operation to prevent duplicate submissions.",
                    type_uri="https://billingbureau.co.za/errors/missing-idempotency-key",
                    instance=request.path
                )

            key = idempotency_key.strip()
            endpoint_scope = scope or request.path

            # Check for existing idempotency record
            existing = IdempotencyRecord.objects.filter(
                idempotency_key=key,
                scope=endpoint_scope
            ).first()

            if existing:
                resp = JsonResponse(existing.response_body, status=existing.status_code)
                resp['Idempotent-Replayed'] = 'true'
                return resp

            # Execute the view
            response = view_func(request, *args, **kwargs)

            # Only cache successful or non-server-error responses
            if isinstance(response, (JsonResponse, HttpResponse)) and response.status_code < 500:
                try:
                    content_str = response.content.decode('utf-8')
                    body_json = json.loads(content_str)
                    user = request.user if request.user.is_authenticated else None

                    IdempotencyRecord.objects.create(
                        idempotency_key=key,
                        scope=endpoint_scope,
                        user=user,
                        endpoint=request.path,
                        status_code=response.status_code,
                        response_body=body_json
                    )
                except (ValueError, json.JSONDecodeError):
                    pass

            return response
        return _wrapped_view
    return decorator
