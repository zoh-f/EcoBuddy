from django.db import models
from django.contrib.auth.models import User

class ChatRoom(models.Model):
    name = models.CharField(max_length=255, blank=True)  # optional room name
    participants = models.ManyToManyField(User, related_name="chat_rooms")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def get_display_name(self):
        return ", ".join([u.username for u in self.participants.all()])

    def __str__(self):
        return self.name or f"ChatRoom {self.id}"

class Message(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages", null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    # Moderation fields
    is_removed = models.BooleanField(default=False, help_text="Whether this message has been removed by a moderator")
    removed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages_removed',
        help_text="Moderator who removed this message"
    )
    removed_at = models.DateTimeField(null=True, blank=True)
    removal_reason = models.TextField(blank=True, help_text="Reason for removal")

    def __str__(self):
        return f"{self.sender.username}: {self.content[:20]}"
