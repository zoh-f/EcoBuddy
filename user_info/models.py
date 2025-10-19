# user_info/models.py
from django.db import models
from django.core.validators import RegexValidator

username_validator = RegexValidator(
    regex=r'^[\w.-]+$',
    message="Username may contain letters, digits, underscores, dots, and hyphens."
)

class UserInfo(models.Model):
    username  = models.CharField(
        max_length=30,
        unique=True,
        validators=[username_validator],
        help_text="Public handle (unique)."
    )
    pronoun   = models.CharField(max_length=50, blank=True)  # optional
    email     = models.EmailField(blank=True)                # populated from Google login
    bio       = models.TextField(blank=True)                 # optional
    join_date = models.DateTimeField(auto_now_add=True)      # set once at create

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"{self.username}"

    def to_dict(self):
        return {
            "username": self.username,
            "pronoun": self.pronoun or None,
            "email": self.email or None,
            "join_date": self.join_date.strftime("%Y-%m-%d %H:%M:%S"),
            "bio": self.bio or None,
        }
