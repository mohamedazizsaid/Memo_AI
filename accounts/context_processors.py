"""
MemoAi — Accounts Context Processors
Provides current active language, translation proxy, and locale state to all templates.
"""

from .translations import TranslationProxy, translate_text


def language_context(request):
    """
    Exposes active language code and translation proxy 't' to all templates.
    Resolves language in order of priority:
    1. Authenticated user's UserPreferences.language
    2. Session 'django_language'
    3. Cookie 'django_language'
    4. Default 'fr'
    """
    lang = 'fr'

    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            if hasattr(request.user, 'preferences'):
                lang = request.user.preferences.language or 'fr'
        except Exception:
            pass
    elif hasattr(request, 'session') and request.session.get('django_language'):
        lang = request.session.get('django_language')
    elif hasattr(request, 'COOKIES') and request.COOKIES.get('django_language'):
        lang = request.COOKIES.get('django_language')

    # Normalize to 2-letter code
    lang = 'en' if str(lang).lower().startswith('en') else 'fr'

    return {
        'current_lang': lang,
        'is_en': lang == 'en',
        'is_fr': lang == 'fr',
        't': TranslationProxy(lang),
        'available_languages': [
            {'code': 'fr', 'name': 'Français (France)', 'flag': '🇫🇷'},
            {'code': 'en', 'name': 'English (US)', 'flag': '🇺🇸'},
        ],
    }
