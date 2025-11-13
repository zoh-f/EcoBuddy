from django.shortcuts import render, redirect
from django.contrib.auth import logout
from user_info.models import UserInfo
from .models import Profile
from .forms import ProfileImageForm
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError

# Create your views here.
from django.http import HttpResponse

def home(request):
    # --- Anonymous users see landing page ---
    if not request.user.is_authenticated:
        return render(request, "index.html", {
            "userinfo": None,
            "profile": None,
            "form": None,
        })

    # --- Authenticated users see dashboard/profile ---
    # Ensure a UserInfo exists for this user
    userinfo, _ = UserInfo.objects.get_or_create(
        username=request.user.username,
        defaults={"email": request.user.email}
    )
    if not userinfo.email:
        userinfo.email = request.user.email
        userinfo.save()

    # Ensure a Profile exists
    profile, _ = Profile.objects.get_or_create(user=request.user)

    # Handle POST requests (profile picture, bio, display_name)
    if request.method == "POST":
        # Profile image
        form = ProfileImageForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()

        # Display name & bio
        display_name = request.POST.get("display_name", "").strip()
        bio = request.POST.get("bio", "").strip()

        if display_name:
            userinfo.display_name = display_name
        userinfo.bio = bio  # allow empty

        try:
            userinfo.full_clean()
            userinfo.save()
        except ValidationError as e:
            # optionally handle validation errors
            pass

        return redirect("home")  # reload page

    else:
        form = ProfileImageForm(instance=profile)

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
