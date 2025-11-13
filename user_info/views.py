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
    Create or update a user profile. Supports:
    { "username", "display_name", "pronoun", "email", "bio" }
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    username = payload.get("username")
    if not username:
        return HttpResponseBadRequest("username is required")

    obj, _created = UserInfo.objects.get_or_create(username=username)

    # Update fields if present
    for field in ["display_name", "pronoun", "email", "bio"]:
        if field in payload and payload[field] != "":
            setattr(obj, field, payload[field])

    obj.full_clean()
    obj.save()
    return JsonResponse(obj.to_dict(), status=201 if _created else 200)
