from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .forms import PostForm, ProfileImageForm
from .models import Post, Profile
from user_info.models import UserInfo
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.http import HttpResponse

# Create your views here.

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
    # Get all non-superuser users and their profiles
    users = User.objects.select_related("profile").filter(is_superuser=False)
    profiles_with_info = []
    
    for u in users:
        try:
            info = UserInfo.objects.get(username=u.username)
        except UserInfo.DoesNotExist:
            info = None
        
        profiles_with_info.append({
            "user": u,
            "role": u.profile.role if hasattr(u, "profile") else "N/A",
            "joined_at": u.profile.joined_at if hasattr(u, "profile") else None,
            "display_name": info.display_name if info else u.username,
            "bio": info.bio if info else "",
        })
    
    return render(request, "admin_page.html", {
        "profiles": profiles_with_info
    })

@login_required
def posts_page(request):
    # show ONLY this user's posts
    posts = Post.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "post_page.html", {"posts": posts})

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            return redirect('post_page')
    else:
        form = PostForm()
    return render(request, 'create_post.html', {'form': form})