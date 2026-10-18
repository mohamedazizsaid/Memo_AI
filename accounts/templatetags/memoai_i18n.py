"""
MemoAi — Custom Template Tags and Filters for Platform Translation
"""

from django import template
from accounts.translations import translate_text, TRANSLATIONS

register = template.Library()


@register.filter(name='t', takes_context=True)
def translate_filter(context, value):
    """
    Translates French text to English if active language is 'en'.
    Usage: {{ "Apparence"|t }}
    """
    if not value:
        return ""
    current_lang = context.get('current_lang', 'fr')
    return translate_text(str(value), current_lang)


@register.simple_tag(takes_context=True)
def trans_text(context, fr_text, en_text):
    """
    Outputs French text or English text based on current language.
    Usage: {% trans_text "Enregistrer" "Save" %}
    """
    current_lang = context.get('current_lang', 'fr')
    if current_lang == 'en':
        return en_text
    return fr_text


@register.simple_tag(takes_context=True)
def t_key(context, key):
    """
    Fetches translated string by catalog key.
    Usage: {% t_key 'nav_journal' %}
    """
    current_lang = context.get('current_lang', 'fr')
    catalog = TRANSLATIONS.get(current_lang, TRANSLATIONS['fr'])
    return catalog.get(key, TRANSLATIONS['fr'].get(key, key))
