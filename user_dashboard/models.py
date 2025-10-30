from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from uuid import uuid4
from pathlib import Path

class Profile(models.Model):
    USER = "user"
    ADMIN = "admin"
    ROLE_CHOICES = [
        (USER, "User"),
        (ADMIN, "Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=USER)
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    #TODO: Make sure all users are in admin user_dashboard profile page

def post_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return Path('posts') / filename

class Post(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, default="Sustainability Post")
    content = models.TextField()
    photo = models.ImageField(upload_to=post_photo_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Post by {self.user.username} at {self.created_at}"