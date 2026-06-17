from django.db import models
from django.contrib.auth.models import User

class Conversation(models.Model):
    CONVERSATION_TYPE_CHOICES = (
        ('private', 'Private Chat'),
        ('group', 'Group Chat'),
    )
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True)
    conversation_type = models.CharField(max_length=10, choices=CONVERSATION_TYPE_CHOICES, default='private')
    participants = models.ManyToManyField(User, related_name='conversations')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    group_avatar = models.ImageField(upload_to='group_avatars/', null=True, blank=True)

    def __str__(self):
        return self.name or f"Chat {self.id}"

    class Meta:
        ordering = ['-updated_at']


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    image = models.ImageField(upload_to='messages/', blank=True, null=True)
    file = models.FileField(upload_to='messages/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender.username}: {self.text[:50]}"

    class Meta:
        ordering = ['created_at']


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'emoji')

