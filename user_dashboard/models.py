from django.db import models
from django.contrib.auth.models import User

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