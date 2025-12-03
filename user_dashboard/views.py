from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .forms import PostForm, ProfileImageForm
from .models import Post, Profile, Flag, Friendship, FriendRequest
from user_info.models import UserInfo
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from .decorators import moderator_required
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

            if post.is_draft:
                messages.success(request, "Post saved as draft!")
                return redirect('drafts_page')
            else:
                messages.success(request, "Post published!")
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


        from messaging.models import ChatRoom

        user_chat_rooms = ChatRoom.objects.filter(participants=user)

        for chat_room in user_chat_rooms:
            # Remove user from participants
            chat_room.participants.remove(user)

            # If chat room is now empty, delete it
            if chat_room.participants.count() == 0:
                chat_room.delete()
                print(f"✅ Deleted empty chat room: {chat_room.id}")

        try:
            user_info = UserInfo.objects.get(username=user.username)
            user_info.delete()
            print(f"✅ Deleted UserInfo for {user.username}")
        except UserInfo.DoesNotExist:
            print(f"ℹ️  No UserInfo found for {user.username}")
            pass

        username = user.username  # Save for logging
        logout(request)


        user.delete()
        print(f"✅ Deleted user account: {username}")

        # summary logging
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

        messages.success(
            request,
            f"Your account has been successfully deleted. "
            f"We deleted {len(deleted_files)} file(s) from our servers. "
            f"Goodbye, {username}!"
        )

        return redirect('/')


# Moderation Views

@login_required
def flag_content(request):
    """Allow users to flag inappropriate content using query params"""
    content_type = request.GET.get('type')
    content_id = request.GET.get('id')

    if request.method == 'POST':
        reason = request.POST.get('reason')
        description = request.POST.get('description', '')

        Flag.objects.create(
            reporter=request.user,
            content_type=content_type,
            content_id=content_id,
            reason=reason,
            description=description,
            status=Flag.PENDING
        )

        messages.success(request, "Thank you for reporting. Our moderators will review this content.")
        return redirect('home')

    return render(request, 'user_dashboard/flag_form.html', {
        'content_type': content_type,
        'content_id': content_id
    })


@login_required
@moderator_required
def moderation_dashboard(request):
    """Main moderator dashboard"""
    pending_flags = Flag.objects.filter(status=Flag.PENDING).select_related('reporter').order_by('-created_at')
    recent_reviews = Flag.objects.exclude(status=Flag.PENDING).select_related('reporter', 'reviewed_by').order_by('-reviewed_at')[:10]

    total_pending = pending_flags.count()
    total_reviewed_today = Flag.objects.filter(reviewed_at__date=timezone.now().date()).count()
    total_suspended = Profile.objects.filter(is_suspended=True).count()

    for flag in pending_flags:
        flag.content_obj = flag.get_content_object()
        flag.flagged_user = flag.get_flagged_user()

    context = {
        'pending_flags': pending_flags,
        'recent_reviews': recent_reviews,
        'total_pending': total_pending,
        'total_reviewed_today': total_reviewed_today,
        'total_suspended': total_suspended,
    }

    return render(request, 'user_dashboard/moderation_dashboard.html', context)


@login_required
@moderator_required
def remove_post(request):
    """Remove a post - uses query params"""
    post_id = request.GET.get('id')
    flag_id = request.GET.get('flag')

    post = get_object_or_404(Post, id=post_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'Violates community standards')

        post.is_removed = True
        post.removed_by = request.user
        post.removed_at = timezone.now()
        post.removal_reason = reason
        post.save()

        if flag_id:
            flag = Flag.objects.get(id=flag_id)
            flag.status = Flag.ACTIONED
            flag.reviewed_by = request.user
            flag.reviewed_at = timezone.now()
            flag.moderator_notes = f"Post removed: {reason}"
            flag.save()

        messages.success(request, f"Post by {post.user.username} has been removed.")
        return redirect('moderation_dashboard')

    return render(request, 'user_dashboard/confirm_removal.html', {'post': post, 'flag_id': flag_id})


@login_required
@moderator_required
def remove_message(request):
    """Remove a message - uses query params"""
    from messaging.models import Message

    message_id = request.GET.get('id')
    flag_id = request.GET.get('flag')

    message = get_object_or_404(Message, id=message_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'Violates community standards')

        message.is_removed = True
        message.removed_by = request.user
        message.removed_at = timezone.now()
        message.removal_reason = reason
        message.save()

        if flag_id:
            flag = Flag.objects.get(id=flag_id)
            flag.status = Flag.ACTIONED
            flag.reviewed_by = request.user
            flag.reviewed_at = timezone.now()
            flag.moderator_notes = f"Message removed: {reason}"
            flag.save()

        messages.success(request, f"Message by {message.sender.username} has been removed.")
        return redirect('moderation_dashboard')

    return render(request, 'user_dashboard/confirm_removal.html', {'message': message, 'flag_id': flag_id})


@login_required
@moderator_required
def dismiss_flag(request):
    """Dismiss a flag - uses query params"""
    flag_id = request.GET.get('id')
    flag = get_object_or_404(Flag, id=flag_id)

    if request.method == 'POST':
        notes = request.POST.get('notes', 'No violation found')

        flag.status = Flag.DISMISSED
        flag.reviewed_by = request.user
        flag.reviewed_at = timezone.now()
        flag.moderator_notes = notes
        flag.save()

        messages.success(request, "Flag dismissed.")
        return redirect('moderation_dashboard')

    return render(request, 'user_dashboard/dismiss_flag.html', {'flag': flag})


# User Suspension Views

@login_required
@moderator_required
def suspend_user(request):
    user_id = request.GET.get('id')
    flag_id = request.GET.get('flag')

    user_to_suspend = get_object_or_404(User, id=user_id)
    profile = user_to_suspend.profile

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()

        if not reason:
            messages.error(request, "Suspension reason is required.")
            return redirect(f"{request.path}?id={user_id}" + (f"&flag={flag_id}" if flag_id else ""))

        profile.is_suspended = True
        profile.suspension_reason = reason
        profile.suspended_at = timezone.now()
        profile.suspended_by = request.user
        profile.save()

        if flag_id:
            flag = Flag.objects.get(id=flag_id)
            flag.status = Flag.ACTIONED
            flag.reviewed_by = request.user
            flag.reviewed_at = timezone.now()
            flag.moderator_notes = f"User suspended: {reason}"
            flag.save()

        messages.success(request, f"User {user_to_suspend.username} has been suspended.")
        return redirect('moderation_dashboard')

    return render(request, 'user_dashboard/suspend_user.html', {
        'user_to_suspend': user_to_suspend,
        'profile': profile,
        'flag_id': flag_id
    })


@login_required
@moderator_required
def reinstate_user(request):
    user_id = request.GET.get('id')
    user_to_reinstate = get_object_or_404(User, id=user_id)
    profile = user_to_reinstate.profile

    if request.method == 'POST':
        profile.is_suspended = False
        profile.reinstated_at = timezone.now()
        profile.reinstated_by = request.user
        profile.save()

        messages.success(request, f"User {user_to_reinstate.username} has been reinstated.")
        return redirect('suspended_users_list')

    return render(request, 'user_dashboard/reinstate_user.html', {
        'user_to_reinstate': user_to_reinstate,
        'profile': profile
    })


def account_suspended(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
        return redirect('home')

    profile = request.user.profile

    if not profile.is_suspended:
        return redirect('home')

    return render(request, 'user_dashboard/account_suspended.html', {'profile': profile})


@login_required
@moderator_required
def suspended_users_list(request):
    suspended_profiles = Profile.objects.filter(is_suspended=True).select_related('user', 'suspended_by')

    return render(request, 'user_dashboard/suspended_users_list.html', {
        'suspended_profiles': suspended_profiles,
        'total_suspended': suspended_profiles.count()
    })