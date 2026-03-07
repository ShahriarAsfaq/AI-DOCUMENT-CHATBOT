import uuid

from django.db import models


class Message(models.Model):
    """A simple chat message stored in DB."""
    user = models.CharField(max_length=255)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user}: {self.text[:50]}"


class ChatSession(models.Model):
    """Chat session for tracking conversation history."""
    session_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Session {self.session_id}"


class ChatMessage(models.Model):
    """Individual message in a chat session."""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, db_index=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    similarity_score = models.FloatField(null=True, blank=True, db_index=True)
    source_page = models.IntegerField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['session', 'timestamp']),
            models.Index(fields=['role']),
            models.Index(fields=['similarity_score']),
            models.Index(fields=['source_page']),
        ]
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
