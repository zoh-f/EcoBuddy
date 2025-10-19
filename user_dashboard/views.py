from django.shortcuts import render, redirect
from django.contrib.auth import logout
from user_info.models import UserInfo
from .models import Profile

# Create your views here.
from django.http import HttpResponse

def home(request):
    profile = None
    if request.user.is_authenticated:
        try:
            profile, created = UserInfo.objects.get_or_create(username=request.user.username, defaults={"email": request.user.email})
            if profile.email == "":
                profile.email = request.user.email
                profile.save()
        except UserInfo.DoesNotExist:
            profile = None

    return render(request, "index.html", {"profile": profile})

def logout_view(request):
    logout(request)
    return redirect('/')

def admin_page(request):
    profiles = Profile.objects.select_related("user").filter(user__is_superuser=False).order_by("-joined_at")

    context = {
        "profiles": profiles
    }
    return render(request, "admin_page.html", context)