"""
MemoAi — Custom template filters shared by all apps.
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Access dict by variable key in templates: {{ my_dict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''


@register.filter
def mood_emoji(mood):
    emojis = {
        'amazing': '🤩', 'good': '😊', 'neutral': '😐', 'sad': '😢',
        'stressed': '😤', 'anxious': '😰', 'tired': '😴',
        'angry': '😠', 'excited': '🎉', 'grateful': '🙏',
    }
    return emojis.get(mood, '')
