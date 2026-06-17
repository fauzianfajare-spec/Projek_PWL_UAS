from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_online', 'last_seen', 'created_at')
    list_filter = ('is_online', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone')
    readonly_fields = ('last_seen', 'created_at')
