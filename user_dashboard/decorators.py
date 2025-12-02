from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def moderator_required(view_func):
    """Require moderator or admin role"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect('home')

        if not hasattr(request.user, 'profile'):
            messages.error(request, "You don't have permission to access this page.")
            return redirect('home')

        if not request.user.profile.can_moderate():
            messages.error(request, "You must be a moderator to access this page.")
            return redirect('home')

        return view_func(request, *args, **kwargs)

    return wrapper
