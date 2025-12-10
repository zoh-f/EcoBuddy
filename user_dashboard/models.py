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
    preferred_topics = models.TextField(blank=True, default="")
    first_time_complete = models.BooleanField(default=False)

    profile_picture = models.ImageField(
        upload_to = "profile_pictures/",
        blank=True,
        null=True
    )

    # Suspension fields
    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.TextField(blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users_suspended'
    )
    reinstated_at = models.DateTimeField(null=True, blank=True)
    reinstated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users_reinstated'
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
    # Topic choices for sustainability posts
    TOPIC_CHOICES = [
        ('recycling', '♻️ Recycling & Waste'),
        ('living', '🌱 Sustainable Living'),
        ('campus', '🍃 Campus Sustainability'),
        ('food', '🥗 Food & Dining'),
        ('transport', '🚴 Transportation'),
        ('education', '💡 Tips & Education'),
        ('achievements', '🏆 Achievements'),
        ('discussion', '💬 General Discussion'),
    ]

    # Privacy choices
    PUBLIC = 'public'
    PRIVATE = 'private'
    PRIVACY_CHOICES = [
        (PUBLIC, 'Public'),
        (PRIVATE, 'Friends Only'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, default="Sustainability Post")
    content = models.TextField()
    photo = models.ImageField(upload_to=post_photo_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Social feed fields
    topic = models.CharField(
        max_length=20,
        choices=TOPIC_CHOICES,
        default='discussion',
        help_text="Sustainability topic category"
    )
    privacy = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default=PUBLIC,
        help_text="Who can see this post"
    )
    hashtags = models.TextField(
        blank=True,
        help_text="Comma-separated hashtags (e.g., zerowaste, climateaction)"
    )
    is_draft = models.BooleanField(
        default=False,
        help_text="Draft posts are not shown in feed"
    )
    comments_count = models.IntegerField(
        default=0,
        help_text="Reserved for future Comment feature"
    )
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='liked_posts',
        blank=True,
        help_text="Users who liked this post"
    )

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
        indexes = [
            models.Index(fields=['privacy', 'is_draft', '-created_at']),
            models.Index(fields=['topic', '-created_at']),
            models.Index(fields=['user', 'is_draft']),
        ]

    def __str__(self):
        return f"Post by {self.user.username} at {self.created_at}"

    def get_hashtags_list(self):
        """Parse hashtags from comma-separated string"""
        if not self.hashtags:
            return []
        return [tag.strip().lower() for tag in self.hashtags.split(',') if tag.strip()]

    def get_hashtags_display(self):
        """Return hashtags formatted for display (with # prefix)"""
        return [f"#{tag}" for tag in self.get_hashtags_list()]


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


class Friendship(models.Model):
    """Bidirectional friendship between users"""
    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friendships_as_user1'
    )
    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friendships_as_user2'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user1', 'user2'], name='unique_friendship'),
            models.CheckConstraint(
                condition=models.Q(user1__lt=models.F('user2')),
                name='user1_less_than_user2'
            )
        ]
        indexes = [
            models.Index(fields=['user1', 'user2']),
        ]

    def __str__(self):
        return f"{self.user1.username} <-> {self.user2.username}"

    @classmethod
    def are_friends(cls, user_a, user_b):
        """Check if two users are friends"""
        if user_a.id == user_b.id:
            return False
        u1, u2 = (user_a, user_b) if user_a.id < user_b.id else (user_b, user_a)
        return cls.objects.filter(user1=u1, user2=u2).exists()

    @classmethod
    def get_friends(cls, user):
        """Get all friends of a user"""
        from django.db.models import Q
        friendships = cls.objects.filter(Q(user1=user) | Q(user2=user))
        friend_ids = []
        for f in friendships:
            friend_ids.append(f.user2.id if f.user1 == user else f.user1.id)
        return User.objects.filter(id__in=friend_ids)

    @classmethod
    def create_friendship(cls, user_a, user_b):
        """Create friendship (normalizes order)"""
        if user_a.id == user_b.id:
            return None
        u1, u2 = (user_a, user_b) if user_a.id < user_b.id else (user_b, user_a)
        friendship, created = cls.objects.get_or_create(user1=u1, user2=u2)
        return friendship

    @classmethod
    def remove_friendship(cls, user_a, user_b):
        """Remove friendship"""
        if user_a.id == user_b.id:
            return
        u1, u2 = (user_a, user_b) if user_a.id < user_b.id else (user_b, user_a)
        cls.objects.filter(user1=u1, user2=u2).delete()


class FriendRequest(models.Model):
    """Friend request from one user to another"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friend_requests_sent'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friend_requests_received'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['from_user', 'to_user'],
                condition=models.Q(status='pending'),
                name='unique_pending_request'
            )
        ]
        indexes = [
            models.Index(fields=['to_user', 'status']),
            models.Index(fields=['from_user', 'status']),
        ]

    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username} ({self.status})"


class Notification(models.Model):
    """In-app notifications for user activities"""

    # Notification type choices
    FRIEND_REQUEST = 'friend_request'
    FRIEND_ACCEPT = 'friend_accept'
    FRIEND_REMOVED = 'friend_removed'
    POST_LIKE = 'post_like'
    NEW_MESSAGE = 'new_message'
    POST_REMOVED = 'post_removed'
    MESSAGE_REMOVED = 'message_removed'
    ACCOUNT_SUSPENDED = 'account_suspended'
    ACCOUNT_REINSTATED = 'account_reinstated'

    NOTIFICATION_TYPE_CHOICES = [
        (FRIEND_REQUEST, 'Friend Request'),
        (FRIEND_ACCEPT, 'Friend Request Accepted'),
        (FRIEND_REMOVED, 'Friend Removed'),
        (POST_LIKE, 'Post Liked'),
        (NEW_MESSAGE, 'New Message'),
        (POST_REMOVED, 'Post Removed'),
        (MESSAGE_REMOVED, 'Message Removed'),
        (ACCOUNT_SUSPENDED, 'Account Suspended'),
        (ACCOUNT_REINSTATED, 'Account Reinstated'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="User who receives this notification"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications_sent',
        help_text="User who triggered this notification"
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPE_CHOICES
    )
    message = models.CharField(
        max_length=255,
        help_text="Human-readable notification message"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['recipient', '-created_at']),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message[:50]}"