from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from .models import Profile

ADMIN_EMAIL = "swe.project.b15@gmail.com"

User = get_user_model()

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        profile, _ = Profile.objects.get_or_create(user=instance)

    

def make_google_admin(sender, instance, created, **kwargs):
    if instance.email == ADMIN_EMAIL:
        instance.is_staff = True
        instance.is_superuser = True
        instance.save()