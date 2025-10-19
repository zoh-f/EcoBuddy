from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if request.user.is_authenticated:
            return

        email = sociallogin.account.extra_data.get("email")
        if not email:
            return

        try:
            user = User.objects.get(email__iexact=email)
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass
