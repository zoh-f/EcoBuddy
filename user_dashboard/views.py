from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .forms import PostForm, ProfileImageForm
from .models import Post, Profile, Flag, Friendship, FriendRequest
from user_info.models import UserInfo
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from .decorators import moderator_required
from .notifications import (
    notify_friend_request, notify_friend_accepted, notify_post_liked,
    notify_post_removed, notify_message_removed, notify_account_suspended,
    notify_account_reinstated, notify_friend_removed
)
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
    userinfo, _ = UserInfo.objects.get_or_create(
        username=request.user.username,
        defaults={"email": request.user.email}
    )
    if not userinfo.email:
        userinfo.email = request.user.email
        userinfo.save()

    profile, _ = Profile.objects.get_or_create(user=request.user)
    show_modal = not profile.first_time_complete
    topics = Post.TOPIC_CHOICES
    preferred_topics_list = profile.preferred_topics.split(",") if profile.preferred_topics else []

    # 1) Get this user's non-draft, non-removed posts
    user_posts = Post.objects.filter(
        user=request.user,
        is_draft=False,
        is_removed=False,
    )

    # 2) Which topic VALUES do we actually see?
    topics_used = set(user_posts.values_list("topic", flat=True).distinct())

    # --- DEBUG: log to console ---
    #print("ACHIEVEMENTS DEBUG:",
     #     "posts =", user_posts.count(),
      #    "topics_used =", topics_used)

    achievements = {
        "eco_starter": "living" in topics_used,     # 🌱 Sustainable Living
        "recycler": "recycling" in topics_used,     # ♻️ Recycling & Waste
        "campus_steward": "campus" in topics_used,  # 🍃 Campus Sustainability
        "green_foodie": "food" in topics_used,      # 🥗 Food & Dining
        "eco_commuter": "transport" in topics_used  # 🚴 Transportation
    }

    has_any_achievement = any(achievements.values())

    return render(request, "index.html", {
        "userinfo": userinfo,
        "profile": profile,
        "topics": topics,
        "show_onboarding": show_modal,
        "preferred_topics_list": preferred_topics_list,
        "achievements": achievements,
        "has_any_achievement": has_any_achievement,
    })


    return render(request, "index.html", {
        "userinfo": userinfo,
        "profile": profile,
        "topics": topics,
        "show_onboarding": show_modal,
        "preferred_topics_list": preferred_topics_list,
        "achievements": achievements,   # ← pass to template
    })


def logout_view(request):
    logout(request)
    return redirect('/')

@login_required
def finish_onboarding(request):
    if request.method == "POST":
        ui = request.user.profile
        selected_topics = request.POST.getlist("topics")

        ui.preferred_topics = ",".join(selected_topics)
        ui.first_time_complete = True
        ui.save()

        messages.success(request, "Your preferences have been saved!")
        return redirect("/") 


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
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated_post = form.save(commit=False)
            updated_post.user = request.user
            updated_post.save()

            # Redirect back depending on draft/published
            if updated_post.is_draft:
                messages.success(request, "Draft updated!")
                return redirect('drafts_page')
            else:
                messages.success(request, "Post updated!")
                return redirect('post_page')

    else:
        form = PostForm(instance=post)

    return render(request, 'edit_post.html', {
        'form': form,
        'post': post,
    })

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)

    if request.method == "POST":
        # Delete image file from storage
        if post.photo:
            post.photo.delete(save=False)

        post.delete()
        messages.success(request, "Post deleted successfully.")
        return redirect("post_page")

    return render(request, "confirm_delete_post.html", {"post": post})

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

    # Handle POST requests (profile picture, bio, display_name, email, pronoun, topics)
    if request.method == "POST":
        form_type = request.POST.get("form_type", "")
        
        # Handle topic preferences update
        if form_type == "topics":
            selected_topics = request.POST.getlist("preferred_topics")
            profile.preferred_topics = ",".join(selected_topics)
            profile.save()
            messages.success(request, "Topic preferences updated successfully!")
            return redirect("account_settings")
        
        # Handle profile picture deletion
        if request.POST.get("delete_picture") == "true":
            if profile.profile_picture:
                profile.profile_picture.delete(save=True)
                messages.success(request, "Profile picture deleted successfully!")
            return redirect("account_settings")
        
        # Profile image upload
        form = ProfileImageForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile picture updated successfully!")

        # Update all editable fields
        display_name = request.POST.get("display_name", "").strip()
        email = request.POST.get("email", "").strip()
        pronoun = request.POST.get("pronoun", "").strip()
        bio = request.POST.get("bio", "").strip()

        # Update User model email
        if email and email != request.user.email:
            request.user.email = email
            try:
                request.user.full_clean()
                request.user.save()
            except ValidationError as e:
                messages.error(request, "Invalid email address.")
                return redirect("account_settings")

        # Update UserInfo fields
        if display_name:
            userinfo.display_name = display_name
        userinfo.email = email  # sync with User model
        userinfo.pronoun = pronoun
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

    # Get topic choices and user's preferred topics
    from user_dashboard.models import Post
    topics = Post.TOPIC_CHOICES
    preferred_topics_list = profile.preferred_topics.split(",") if profile.preferred_topics else []

    return render(request, 'user_dashboard/account_settings.html', {
        'form': form,
        'profile': profile,
        'userinfo': userinfo,
        'topics': topics,
        'preferred_topics_list': preferred_topics_list,
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
        notify_post_removed(post, request.user, reason)

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
        notify_message_removed(message, request.user, reason)

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
        notify_account_suspended(user_to_suspend, request.user, reason)

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
        notify_account_reinstated(user_to_reinstate, request.user)

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
    
    # ============= PUBLIC FEED =============

@login_required
def public_feed(request):
    """
    Show PUBLIC posts + friends' PRIVATE posts
    Defaults to filtering by user's preferred topics unless ?mode=all
    """

    from django.db.models import Q
    from datetime import timedelta

    # Get mode: preferred (default) or all
    mode = request.GET.get("mode", "preferred")

    # Get friend IDs
    friend_ids = Friendship.get_friends(request.user).values_list('id', flat=True)

    # Base query
    base = Q(is_draft=False, is_removed=False)
    visibility = Q(privacy=Post.PUBLIC) | Q(privacy=Post.PRIVATE, user_id__in=friend_ids)

    posts = Post.objects.filter(base & visibility)

    # --- Load preferred topics ---
    profile = request.user.profile
    preferred_topics = profile.preferred_topics.split(",") if profile.preferred_topics else []

    # --- Topic Filter ---
    topic = request.GET.get('topic')

    if topic == 'preferred' and preferred_topics:
        # User wants preferred topics
        posts = posts.filter(topic__in=preferred_topics)
        active_topic_button = 'preferred'
    elif topic == 'all' or not topic:
        # Show all topics
        active_topic_button = 'all'
        # no filtering needed
    else:
        # Specific topic selected
        posts = posts.filter(topic=topic)
        active_topic_button = topic


    # --- Hashtag Filter ---
    hashtag = request.GET.get('hashtag', '').strip().lower().lstrip('#')
    if hashtag:
        posts = posts.filter(hashtags__icontains=hashtag)

    # --- Time Filter ---
    days = request.GET.get('days')
    if days:
        try:
            cutoff = timezone.now() - timedelta(days=int(days))
            posts = posts.filter(created_at__gte=cutoff)
        except ValueError:
            pass

    # --- Search Filter ---
    search = request.GET.get('search', '').strip()
    if search:
        posts = posts.filter(
            Q(content__icontains=search) |
            Q(title__icontains=search)
        )

    # Optimize DB queries
    posts = posts.select_related('user', 'user__profile').order_by('-created_at')

    # Add display names
    for post in posts:
        try:
            ui = UserInfo.objects.get(username=post.user.username)
            post.author_display_name = ui.display_name or post.user.username
        except UserInfo.DoesNotExist:
            post.author_display_name = post.user.username

    context = {
        'posts': posts,
        'topic_choices': Post.TOPIC_CHOICES,
        'current_topic': topic or 'all',
        'preferred_topics': preferred_topics,
        'active_topic_button': active_topic_button,
        'mode': mode,  # ← NEW
        'current_hashtag': hashtag,
        'current_days': days,
        'current_search': search,
    }

    return render(request, 'user_dashboard/feed.html', context)



# ============= FRIEND SYSTEM =============

@login_required
def send_friend_request(request):
    """Send friend request - ?username=..."""
    username = request.GET.get('username')
    to_user = get_object_or_404(User, username=username)

    if to_user == request.user:
        messages.error(request, "Cannot send request to yourself.")
        return redirect('user_profile', username=username)

    if Friendship.are_friends(request.user, to_user):
        messages.info(request, f"Already friends with {to_user.username}.")
        return redirect('user_profile', username=username)

    # Check existing/reverse requests
    existing = FriendRequest.objects.filter(
        from_user=request.user, to_user=to_user, status='pending'
    ).first()

    if existing:
        messages.info(request, "Friend request already sent.")
        return redirect('user_profile', username=username)

    reverse = FriendRequest.objects.filter(
        from_user=to_user, to_user=request.user, status='pending'
    ).first()

    if reverse:
        messages.info(request, f"{to_user.username} already sent you a request!")
        return redirect('friends_list')

    FriendRequest.objects.create(from_user=request.user, to_user=to_user)
    notify_friend_request(request.user, to_user)
    messages.success(request, f"Friend request sent to {to_user.username}!")
    return redirect('user_profile', username=username)


@login_required
def accept_friend_request(request):
    """Accept request - ?id=..."""
    request_id = request.GET.get('id')
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)

    if friend_request.status != 'pending':
        messages.error(request, "Request already processed.")
        return redirect('friends_list')

    friend_request.status = 'accepted'
    friend_request.responded_at = timezone.now()
    friend_request.save()

    Friendship.create_friendship(request.user, friend_request.from_user)
    notify_friend_accepted(request.user, friend_request.from_user)

    messages.success(request, f"Now friends with {friend_request.from_user.username}!")
    return redirect('friends_list')


@login_required
def reject_friend_request(request):
    """Reject request - ?id=..."""
    request_id = request.GET.get('id')
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)

    if friend_request.status != 'pending':
        messages.error(request, "Request already processed.")
        return redirect('friends_list')

    friend_request.status = 'rejected'
    friend_request.responded_at = timezone.now()
    friend_request.save()

    messages.success(request, "Friend request rejected.")
    return redirect('friends_list')


@login_required
def unfriend(request):
    """Remove friendship - ?username=... with POST confirmation"""
    username = request.GET.get('username')
    friend = get_object_or_404(User, username=username)

    if request.method == 'POST':
        Friendship.remove_friendship(request.user, friend)
        notify_friend_removed(request.user, friend)
        messages.success(request, f"No longer friends with {friend.username}.")
        return redirect('friends_list')

    return render(request, 'user_dashboard/confirm_unfriend.html', {'friend': friend})


@login_required
def friends_list(request):
    """Show friends and pending requests"""
    friends = Friendship.get_friends(request.user)

    # Add display names
    friends_with_info = []
    for friend in friends:
        try:
            userinfo = UserInfo.objects.get(username=friend.username)
            display_name = userinfo.display_name or friend.username
        except UserInfo.DoesNotExist:
            display_name = friend.username
        friends_with_info.append({'user': friend, 'display_name': display_name})

    # Pending requests received
    pending_requests = FriendRequest.objects.filter(
        to_user=request.user, status='pending'
    ).select_related('from_user')

    for req in pending_requests:
        try:
            userinfo = UserInfo.objects.get(username=req.from_user.username)
            req.display_name = userinfo.display_name or req.from_user.username
        except UserInfo.DoesNotExist:
            req.display_name = req.from_user.username

    # Sent requests
    sent_requests = FriendRequest.objects.filter(
        from_user=request.user, status='pending'
    ).select_related('to_user')

    for req in sent_requests:
        try:
            userinfo = UserInfo.objects.get(username=req.to_user.username)
            req.display_name = userinfo.display_name or req.to_user.username
        except UserInfo.DoesNotExist:
            req.display_name = req.to_user.username

    context = {
        'friends': friends_with_info,
        'pending_requests': pending_requests,
        'sent_requests': sent_requests,
    }
    return render(request, 'user_dashboard/friends_list.html', context)


# ============= USER PROFILES =============

@login_required
def user_profile(request, username):
    """Public user profile with posts and friend status"""
    profile_user = get_object_or_404(User, username=username)

    try:
        userinfo = UserInfo.objects.get(username=username)
    except UserInfo.DoesNotExist:
        userinfo = None

    try:
        profile = Profile.objects.get(user=profile_user)
    except Profile.DoesNotExist:
        profile = None

    is_own_profile = (profile_user == request.user)
    is_friend = Friendship.are_friends(request.user, profile_user)

    pending_request_sent = FriendRequest.objects.filter(
        from_user=request.user, to_user=profile_user, status='pending'
    ).exists()

    pending_request_received = FriendRequest.objects.filter(
        from_user=profile_user, to_user=request.user, status='pending'
    ).exists()

    # Posts visibility
    if is_own_profile:
        posts = Post.objects.filter(user=profile_user, is_draft=False, is_removed=False)
    elif is_friend:
        posts = Post.objects.filter(user=profile_user, is_draft=False, is_removed=False)
    else:
        posts = Post.objects.filter(user=profile_user, privacy=Post.PUBLIC, is_draft=False, is_removed=False)

    posts = posts.order_by('-created_at')

    context = {
        'profile_user': profile_user,
        'userinfo': userinfo,
        'profile': profile,
        'posts': posts,
        'is_own_profile': is_own_profile,
        'is_friend': is_friend,
        'pending_request_sent': pending_request_sent,
        'pending_request_received': pending_request_received,
    }
    return render(request, 'user_dashboard/user_profile.html', context)


@login_required
def user_search(request):
    """Search for users by username or display name"""
    query = request.GET.get('q', '').strip()

    results = []
    if query:
        # Search in User.username
        user_results = User.objects.filter(username__icontains=query).exclude(id=request.user.id)[:20]

        for user in user_results:
            try:
                userinfo = UserInfo.objects.get(username=user.username)
                display_name = userinfo.display_name or user.username
            except UserInfo.DoesNotExist:
                display_name = user.username

            # Check friendship status
            is_friend = Friendship.are_friends(request.user, user)

            # Check pending request
            pending_sent = FriendRequest.objects.filter(
                from_user=request.user, to_user=user, status='pending'
            ).exists()

            pending_received = FriendRequest.objects.filter(
                from_user=user, to_user=request.user, status='pending'
            ).exists()

            results.append({
                'user': user,
                'display_name': display_name,
                'is_friend': is_friend,
                'pending_sent': pending_sent,
                'pending_received': pending_received,
            })

    return render(request, 'user_dashboard/user_search.html', {
        'results': results,
        'query': query
    })


# ============= DRAFTS SYSTEM =============

@login_required
def drafts_page(request):
    """Show user's draft posts"""
    drafts = Post.objects.filter(user=request.user, is_draft=True).order_by('-created_at')
    return render(request, 'user_dashboard/drafts.html', {'drafts': drafts})


@login_required
def publish_draft(request):
    """Publish draft - ?id=... with POST confirmation"""
    post_id = request.GET.get('id')
    post = get_object_or_404(Post, id=post_id, user=request.user, is_draft=True)

    if request.method == 'POST':
        post.is_draft = False
        post.save()
        messages.success(request, "Post published!")
        return redirect('post_page')

    return render(request, 'user_dashboard/confirm_publish.html', {'post': post})

# ========== LIKE/UNLIKE FEATURE =========
@login_required
def toggle_like(request, post_id):
    post=get_object_or_404(Post, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
        notify_post_liked(request.user, post)
    if request.headers.get("X-Requested-With")=="XMLHttpRequest":
        return JsonResponse({
            "liked": liked,
            "like_count": post.likes.count()
        })
    return redirect(request.META.get("HTTP_REFERER", "public_feed"))


# ========== NOTIFICATIONS =========
from .models import Notification

@login_required
def notifications_page(request):
    """Display all notifications for the current user"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender').order_by('-created_at')[:50]

    unread_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    return render(request, 'user_dashboard/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read for current user"""
    if request.method == 'POST':
        Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect('notifications')
