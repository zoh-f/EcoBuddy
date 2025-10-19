# user_info/views.py
import json
from django.http import JsonResponse, Http404, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from .models import UserInfo

@require_http_methods(["GET"])
def public_profile(request, username):
    """
    PUBLIC: only returns the fields from UserInfo (no private names, etc.)
    """
    try:
        u = UserInfo.objects.get(username=username)
    except UserInfo.DoesNotExist:
        raise Http404("Profile not found")
    return JsonResponse(u.to_dict())

@require_http_methods(["POST"])
def upsert_profile(request):
    """
    Minimal create/update endpoint (no UI). Expects JSON body with any of:
    { "username", "pronoun", "email", "bio" }
    - If username exists: updates that record.
    - Else: creates a new record.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    username = payload.get("username")
    if not username:
        return HttpResponseBadRequest("username is required")

    obj, _created = UserInfo.objects.get_or_create(username=username)
    # Only update fields that are present (and not empty string)
    for field in ["pronoun", "email", "bio"]:
        if field in payload and payload[field] != "":
            setattr(obj, field, payload[field])

    obj.full_clean()  # run validators (e.g., username regex, email format)
    obj.save()
    return JsonResponse(obj.to_dict(), status=201 if _created else 200)
