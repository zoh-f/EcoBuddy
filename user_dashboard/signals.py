from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from .models import Profile

ADMIN_EMAIL = ["swe.project.b15@gmail.com", "admin@gmail.com"]

User = get_user_model()

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        profile, _ = Profile.objects.get_or_create(user=instance)

    # Check if user should be promoted to admin (works for both new and existing users)
    if instance.email in ADMIN_EMAIL:
        # Update User model permissions
        if not instance.is_staff or not instance.is_superuser:
            User.objects.filter(pk=instance.pk).update(
                is_staff=True,
                is_superuser=True
            )

        # Update Profile role
        profile, _ = Profile.objects.get_or_create(user=instance)
        if profile.role != Profile.ADMIN:
            profile.role = Profile.ADMIN
            profile.save()