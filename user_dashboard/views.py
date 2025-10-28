from django.shortcuts import render, redirect
from django.contrib.auth import logout
from user_info.models import UserInfo
from .models import Profile
from .forms import ProfileImageForm
from django.contrib.auth.decorators import login_required

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
# userinfo = None   # from UserInfo model
#     profile = None    # from Profile model (has profile_picture, bio, etc.)
#     form = None       # ProfileImageForm for upload

#     if request.user.is_authenticated:
#         # Make sure there's a UserInfo row for this user
#         userinfo, _ = UserInfo.objects.get_or_create(
#             username=request.user.username,
#             defaults={"email": request.user.email}
#         )
#         if userinfo.email == "":
#             userinfo.email = request.user.email
#             userinfo.save()

#         # Get or create Profile row
#         # (Signals should have created it already, but this is safe for older users too.)
#         profile, _ = Profile.objects.get_or_create(user=request.user)

#         # Handle picture upload
#         if request.method == "POST":
#             form = ProfileImageForm(request.POST, request.FILES, instance=profile)
#             if form.is_valid():
#                 form.save()  # uploads to S3
#                 return redirect("home")
#         else:
#             form = ProfileImageForm(instance=profile)

#     return render(
#         request,
#         "index.html",
#         {
#             "userinfo": userinfo,
#             "profile": profile,
#             "form": form,
#         },
#     )