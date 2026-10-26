"""
MemoAi — Custom template filters shared by all apps.
"""
import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import normalize_newlines

register = template.Library()

# The journal editor only supports **bold** and *italic* (see journal/form.html).
_BOLD_RE = re.compile(r'\*\*(?=\S)([^*\n]+?)(?<=\S)\*\*')
_ITALIC_RE = re.compile(r'(?<!\*)\*(?=\S)([^*\n]+?)(?<=\S)\*(?!\*)')


@register.filter
def rich_text(value):
    """
    Render the journal editor's tiny markdown subset, safely.

    The value is HTML-escaped *before* the markers are converted, so a user can
    never inject markup through their entry.
    """
    if value is None:
        return ''

    text = escape(normalize_newlines(str(value)))
    text = _BOLD_RE.sub(r'<strong>\1</strong>', text)
    text = _ITALIC_RE.sub(r'<em>\1</em>', text)

    paragraphs = [block.strip() for block in re.split(r'\n{2,}', text.strip()) if block.strip()]
    if not paragraphs:
        return ''
    return mark_safe(''.join(
        '<p>{}</p>'.format(block.replace('\n', '<br>')) for block in paragraphs
    ))


@register.filter
def get_item(dictionary, key):
    """Access dict by variable key in templates: {{ my_dict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''


@register.filter
def mood_emoji(mood):
    from common.icons import get_mood_svg
    return get_mood_svg(mood)

