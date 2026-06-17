from django import template
from django.templatetags.static import static

register = template.Library()

@register.filter
def avatar_url(user_profile):
    """Get avatar URL with fallback to placeholder"""
    if user_profile and user_profile.avatar:
        return user_profile.avatar.url
    return 'https://ui-avatars.com/api/?name=' + user_profile.user.username

@register.filter
def group_avatar_url(group_avatar, group_name):
    """Get group avatar URL with fallback"""
    if group_avatar:
        return group_avatar.url
    return 'https://ui-avatars.com/api/?name=' + group_name
