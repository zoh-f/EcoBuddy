from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .forms import PostForm
from .models import Post
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
            return redirect('home')
    else:
        form = PostForm()
    return render(request, 'create_post.html', {'form': form})