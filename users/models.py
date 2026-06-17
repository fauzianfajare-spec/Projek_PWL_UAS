from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username
    
    def get_avatar_url(self):
        """Get avatar URL with fallback to placeholder"""
        if self.avatar:
            return self.avatar.url
        return f'https://ui-avatars.com/api/?name={self.user.username}&background=667eea&color=fff'
