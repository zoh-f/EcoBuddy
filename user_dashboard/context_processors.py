"""
Context processors for user_dashboard app.
Makes notification count available globally in all templates.
"""
from .models import Notification


def notification_count(request):
    """
    Add unread notification count to template context.
    Available in all templates as {{ unread_notifications_count }}
    """
    if request.user.is_authenticated:
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}
