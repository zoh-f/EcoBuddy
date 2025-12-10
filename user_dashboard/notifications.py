"""
Notification helper functions for creating various notification types.
"""
from .models import Notification


def create_notification(recipient, notification_type, sender=None, message=""):
    """
    Generic function to create a notification.
    Don't notify users about their own actions.
    """
    if sender and sender == recipient:
        return None

    return Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        message=message
    )


def get_display_name(user):
    """Get display name for a user, falling back to username"""
    from user_info.models import UserInfo
    try:
        userinfo = UserInfo.objects.get(username=user.username)
        return userinfo.display_name or user.username
    except UserInfo.DoesNotExist:
        return user.username


def notify_friend_request(from_user, to_user):
    """Notify user of incoming friend request"""
    display_name = get_display_name(from_user)
    return create_notification(
        recipient=to_user,
        sender=from_user,
        notification_type=Notification.FRIEND_REQUEST,
        message=f"{display_name} sent you a friend request"
    )


def notify_friend_accepted(from_user, to_user):
    """Notify user that their friend request was accepted"""
    display_name = get_display_name(from_user)
    return create_notification(
        recipient=to_user,
        sender=from_user,
        notification_type=Notification.FRIEND_ACCEPT,
        message=f"{display_name} accepted your friend request"
    )


def notify_friend_removed(from_user, removed_user):
    """Notify user that they have been removed as a friend"""
    display_name = get_display_name(from_user)
    return create_notification(
        recipient=removed_user,
        sender=from_user,
        notification_type=Notification.FRIEND_REMOVED,
        message=f"{display_name} removed you from their friends list"
    )


def notify_post_liked(liker, post):
    """Notify post owner that their post was liked"""
    if liker == post.user:
        return None

    display_name = get_display_name(liker)
    return create_notification(
        recipient=post.user,
        sender=liker,
        notification_type=Notification.POST_LIKE,
        message=f"{display_name} liked your post"
    )


def notify_new_message(sender_user, chat_room):
    """Notify chat room participants of a new message"""
    display_name = get_display_name(sender_user)
    notifications = []

    for participant in chat_room.participants.exclude(id=sender_user.id):
        notif = create_notification(
            recipient=participant,
            sender=sender_user,
            notification_type=Notification.NEW_MESSAGE,
            message=f"{display_name} sent a message"
        )
        if notif:
            notifications.append(notif)

    return notifications


def notify_post_removed(post, moderator, reason):
    """Notify post owner that their post was removed"""
    return create_notification(
        recipient=post.user,
        sender=moderator,
        notification_type=Notification.POST_REMOVED,
        message=f"Your post was removed by a moderator: {reason[:100]}"
    )


def notify_message_removed(message, moderator, reason):
    """Notify message sender that their message was removed"""
    if not message.sender:
        return None

    return create_notification(
        recipient=message.sender,
        sender=moderator,
        notification_type=Notification.MESSAGE_REMOVED,
        message=f"Your message was removed by a moderator: {reason[:100]}"
    )


def notify_account_suspended(user, moderator, reason):
    """Notify user that their account was suspended"""
    return create_notification(
        recipient=user,
        sender=moderator,
        notification_type=Notification.ACCOUNT_SUSPENDED,
        message=f"Your account has been suspended: {reason[:100]}"
    )


def notify_account_reinstated(user, moderator):
    """Notify user that their account was reinstated"""
    return create_notification(
        recipient=user,
        sender=moderator,
        notification_type=Notification.ACCOUNT_REINSTATED,
        message="Your account has been reinstated. Welcome back!"
    )


def get_unread_count(user):
    """Get count of unread notifications for a user"""
    return Notification.objects.filter(recipient=user, is_read=False).count()
