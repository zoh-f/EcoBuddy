from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .forms import PostForm, ProfileImageForm
from .models import Post, Profile
from user_info.models import UserInfo
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.contrib import messages
from django.conf import settings
import boto3

# Create your views here.

def home(request):
    # --- Anonymous users see landing page ---
    if not request.user.is_authenticated:
        return render(request, "index.html", {
            "userinfo": None,
            "profile": None,
        })

    # --- Authenticated users see dashboard/profile (Read-only) ---
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

    return render(request, "index.html", {
        "userinfo": userinfo,
        "profile": profile,
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

@login_required
def account_settings(request):
    """
    Display the account settings page where users can:
    - Edit their profile (display name, bio)
    - Upload/change profile picture
    - Delete their account

    This page consolidates all account management functionality.
    """
    # Ensure UserInfo and Profile exist for this user
    userinfo, _ = UserInfo.objects.get_or_create(
        username=request.user.username,
        defaults={"email": request.user.email}
    )
    if not userinfo.email:
        userinfo.email = request.user.email
        userinfo.save()

    profile, _ = Profile.objects.get_or_create(user=request.user)

    # Handle POST requests (profile picture, bio, display_name)
    if request.method == "POST":
        # Profile image upload
        form = ProfileImageForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()

        # Display name & bio update
        display_name = request.POST.get("display_name", "").strip()
        bio = request.POST.get("bio", "").strip()

        if display_name:
            userinfo.display_name = display_name
        userinfo.bio = bio  # allow empty

        try:
            userinfo.full_clean()
            userinfo.save()
            messages.success(request, "Profile updated successfully!")
        except ValidationError as e:
            messages.error(request, "There was an error updating your profile.")

        return redirect("account_settings")  # reload settings page
    else:
        form = ProfileImageForm(instance=profile)

    return render(request, 'user_dashboard/account_settings.html', {
        'form': form,
        'profile': profile,
        'userinfo': userinfo,
    })

@login_required
def delete_account(request):
    """
    Handle account deletion with confirmation and S3 cleanup.

    GET: Show confirmation page asking "Are you sure?"
    POST: Actually delete the account and all associated data
    """

    # If user just clicked the delete button, show confirmation page
    if request.method == 'GET':
        return render(request, 'user_dashboard/confirm_delete.html')

    # If user confirmed deletion (clicked "Yes, delete my account")
    if request.method == 'POST':
        user = request.user
        deleted_files = []  # Track what we delete (for logging)
        failed_files = []   # Track failures (for debugging)

        # ═══════════════════════════════════════════════════════
        # STEP 1: Connect to S3
        # ═══════════════════════════════════════════════════════

        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
        except Exception as e:
            print(f"Failed to connect to S3: {e}")
            # Continue anyway - we'll still delete the account
            s3_client = None

        # ═══════════════════════════════════════════════════════
        # STEP 2: Delete Profile Picture from S3
        # ═══════════════════════════════════════════════════════

        if s3_client and hasattr(user, 'profile'):
            profile = user.profile

            # Check if user has a profile picture
            if profile.profile_picture:
                try:
                    # Get the S3 key (file path in S3)
                    # Example: "profile_pictures/user123.jpg"
                    s3_key = profile.profile_picture.name

                    # Delete from S3
                    s3_client.delete_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=s3_key
                    )

                    deleted_files.append(s3_key)
                    print(f"✅ Deleted profile picture: {s3_key}")

                except Exception as e:
                    failed_files.append(f"Profile picture: {e}")
                    print(f"❌ Failed to delete profile picture: {e}")

        # ═══════════════════════════════════════════════════════
        # STEP 3: Delete All Post Photos from S3
        # ═══════════════════════════════════════════════════════

        if s3_client:
            # Get all posts by this user
            user_posts = Post.objects.filter(user=user)

            for post in user_posts:
                # Check if this post has a photo
                if post.photo:
                    try:
                        # Get the S3 key
                        # Example: "posts/a1b2c3d4.jpg"
                        s3_key = post.photo.name

                        # Delete from S3
                        s3_client.delete_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=s3_key
                        )

                        deleted_files.append(s3_key)
                        print(f"✅ Deleted post photo: {s3_key}")

                    except Exception as e:
                        failed_files.append(f"Post photo {post.id}: {e}")
                        print(f"❌ Failed to delete post photo: {e}")

        # ═══════════════════════════════════════════════════════
        # STEP 4: Remove User from All Chat Rooms
        # ═══════════════════════════════════════════════════════

        from messaging.models import ChatRoom

        user_chat_rooms = ChatRoom.objects.filter(participants=user)

        for chat_room in user_chat_rooms:
            # Remove user from participants
            chat_room.participants.remove(user)

            # If chat room is now empty, delete it
            if chat_room.participants.count() == 0:
                chat_room.delete()
                print(f"✅ Deleted empty chat room: {chat_room.id}")

        # ═══════════════════════════════════════════════════════
        # STEP 5: Delete UserInfo Record
        # ═══════════════════════════════════════════════════════

        try:
            user_info = UserInfo.objects.get(username=user.username)
            user_info.delete()
            print(f"✅ Deleted UserInfo for {user.username}")
        except UserInfo.DoesNotExist:
            print(f"ℹ️  No UserInfo found for {user.username}")
            pass

        # ═══════════════════════════════════════════════════════
        # STEP 6: Log Out User (BEFORE deleting User object)
        # ═══════════════════════════════════════════════════════

        username = user.username  # Save for logging
        logout(request)

        # ═══════════════════════════════════════════════════════
        # STEP 7: Delete User Account
        # ═══════════════════════════════════════════════════════
        # This CASCADE deletes:
        #   - Profile (with profile_picture path)
        #   - All Posts (with photo paths)
        #   - All Messages sent by user

        user.delete()
        print(f"✅ Deleted user account: {username}")

        # ═══════════════════════════════════════════════════════
        # STEP 8: Summary Logging (Optional but Helpful)
        # ═══════════════════════════════════════════════════════

        print("\n" + "="*50)
        print(f"Account Deletion Summary for {username}")
        print("="*50)
        print(f"✅ Files deleted from S3: {len(deleted_files)}")
        for file in deleted_files:
            print(f"   - {file}")

        if failed_files:
            print(f"\n❌ Failed deletions: {len(failed_files)}")
            for failure in failed_files:
                print(f"   - {failure}")
        print("="*50 + "\n")

        # ═══════════════════════════════════════════════════════
        # STEP 9: Redirect with Success Message
        # ═══════════════════════════════════════════════════════

        messages.success(
            request,
            f"Your account has been successfully deleted. "
            f"We deleted {len(deleted_files)} file(s) from our servers. "
            f"Goodbye, {username}!"
        )

        return redirect('/')