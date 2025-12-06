from django.shortcuts import redirect
from django.urls import reverse


class SuspensionCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            if request.user.profile.is_suspended:
                allowed_paths = [
                    reverse('account_suspended'),
                    reverse('logout'),
                    '/static/',
                    '/media/',
                ]

                if not any(request.path.startswith(path) for path in allowed_paths):
                    return redirect('account_suspended')

        response = self.get_response(request)
        return response

class FirstTimeSetupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            ui = getattr(request.user, "userinfo", None)
            if ui and not ui.first_time_complete:
                request.show_onboarding_modal = True

        return response
