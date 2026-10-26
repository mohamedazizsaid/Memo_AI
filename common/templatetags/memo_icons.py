from django import template
from django.utils.safestring import mark_safe
from common.icons import get_mood_svg, get_emotion_svg

register = template.Library()


@register.simple_tag
def mood_icon(mood_key, size=None, extra_class=""):
    """Renders the custom vector icon for a mood."""
    if not mood_key:
        return ""
    return get_mood_svg(mood_key, size=size, extra_class=extra_class)


@register.simple_tag
def emotion_icon(emotion_key, size=None, extra_class=""):
    """Renders the custom vector icon for an AI emotion."""
    if not emotion_key:
        return ""
    return get_emotion_svg(emotion_key, size=size, extra_class=extra_class)
