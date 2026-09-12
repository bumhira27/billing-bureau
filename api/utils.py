from django.http import JsonResponse


def problem_details(status: int, title: str, detail: str, type_uri: str = None, instance: str = None, errors: dict = None):
    """
    Constructs an RFC 7807 Problem Details JSON response.
    """
    payload = {
        "type": type_uri or "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
    }
    if instance:
        payload["instance"] = instance
    if errors:
        payload["errors"] = errors

    response = JsonResponse(payload, status=status)
    response['Content-Type'] = 'application/problem+json'
    return response
