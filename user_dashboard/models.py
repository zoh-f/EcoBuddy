from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from uuid import uuid4
from pathlib import Path

class Profile(models.Model):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    ROLE_CHOICES = [
        (USER, "User"),
        (MODERATOR, "Moderator"),
        (ADMIN, "Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=USER)
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    profile_picture = models.ImageField(
        upload_to = "profile_pictures/",
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def is_moderator_or_admin(self):
        """Check if user has moderation permissions"""
        return self.role in [self.MODERATOR, self.ADMIN]

    def can_moderate(self):
        """Alias for is_moderator_or_admin for clarity"""
        return self.is_moderator_or_admin()

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

    # Moderation fields
    is_removed = models.BooleanField(default=False, help_text="Whether this post has been removed by a moderator")
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts_removed',
        help_text="Moderator who removed this post"
    )
    removed_at = models.DateTimeField(null=True, blank=True)
    removal_reason = models.TextField(blank=True, help_text="Reason for removal")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Post by {self.user.username} at {self.created_at}"


class Flag(models.Model):
    """Reports of inappropriate content by users"""

    # Content type choices
    POST = 'post'
    MESSAGE = 'message'
    PROFILE = 'profile'

    CONTENT_TYPE_CHOICES = [
        (POST, 'Post'),
        (MESSAGE, 'Message'),
        (PROFILE, 'Profile'),
    ]

    # Flag status choices
    PENDING = 'pending'
    REVIEWED = 'reviewed'
    DISMISSED = 'dismissed'
    ACTIONED = 'actioned'

    STATUS_CHOICES = [
        (PENDING, 'Pending Review'),
        (REVIEWED, 'Reviewed'),
        (DISMISSED, 'Dismissed - No Action'),
        (ACTIONED, 'Action Taken'),
    ]

    # Reason choices for common issues
    SPAM = 'spam'
    HARASSMENT = 'harassment'
    INAPPROPRIATE = 'inappropriate'
    MISINFORMATION = 'misinformation'
    OTHER = 'other'

    REASON_CHOICES = [
        (SPAM, 'Spam or Advertising'),
        (HARASSMENT, 'Harassment or Bullying'),
        (INAPPROPRIATE, 'Inappropriate Content'),
        (MISINFORMATION, 'Misinformation'),
        (OTHER, 'Other'),
    ]

    # Who reported it
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='flags_reported',
        help_text="User who reported this content"
    )

    # What was reported
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        help_text="Type of content being reported"
    )
    content_id = models.IntegerField(help_text="ID of the flagged item")

    # Why it was reported
    reason = models.CharField(
        max_length=100,
        choices=REASON_CHOICES,
        default=OTHER
    )
    description = models.TextField(
        blank=True,
        help_text="Additional details about why this was flagged"
    )

    # Review status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING
    )

    # Who reviewed it
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flags_reviewed',
        help_text="Moderator who reviewed this flag"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    moderator_notes = models.TextField(
        blank=True,
        help_text="Internal notes from the moderator"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['content_type', 'content_id']),
        ]

    def __str__(self):
        return f"Flag: {self.get_content_type_display()} #{self.content_id} - {self.get_status_display()}"

    def get_content_object(self):
        """Get the actual flagged object"""
        if self.content_type == self.POST:
            try:
                return Post.objects.get(id=self.content_id)
            except Post.DoesNotExist:
                return None
        elif self.content_type == self.MESSAGE:
            from messaging.models import Message
            try:
                return Message.objects.get(id=self.content_id)
            except Message.DoesNotExist:
                return None
        elif self.content_type == self.PROFILE:
            from user_info.models import UserInfo
            try:
                return UserInfo.objects.get(id=self.content_id)
            except UserInfo.DoesNotExist:
                return None
        return None

    def get_flagged_user(self):
        """Get the user who created the flagged content"""
        content = self.get_content_object()
        if content:
            if hasattr(content, 'user'):
                return content.user
            elif hasattr(content, 'sender'):
                return content.sender
        return None