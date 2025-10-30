from django.shortcuts import render, redirect
from django.contrib.auth import logout
from user_info.models import UserInfo
from .models import Profile
from .forms import ProfileImageForm
from django.contrib.auth.decorators import login_required

# Create your views here.
from django.http import HttpResponse

def home(request):
    # If user is not logged in, just show the landing/login page
    if not request.user.is_authenticated:
        return render(request, "index.html", {
            "userinfo": None,
            "profile": None,
            "form": None,
        })

    # If logged in, ensure a UserInfo exists
    userinfo, _ = UserInfo.objects.get_or_create(
        username=request.user.username,
        defaults={"email": request.user.email}
    )

    if userinfo.email == "":
        userinfo.email = request.user.email
        userinfo.save()

    # Ensure a Profile exists
    profile, _ = Profile.objects.get_or_create(user=request.user)

    # Handle image upload
    if request.method == "POST":
        form = ProfileImageForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()     
    else:
        form = ProfileImageForm(instance=profile)

    # Render the logged-in dashboard
    return render(request, "index.html", {
        "userinfo": userinfo,
        "profile": profile,
        "form": form,
    })

def logout_view(request):
    logout(request)
    return redirect('/')

def admin_page(request):
    profiles = Profile.objects.select_related("user").filter(user__is_superuser=False).order_by("-joined_at")

    context = {
        "profiles": profiles
    }
    return render(request, "admin_page.html", context)
