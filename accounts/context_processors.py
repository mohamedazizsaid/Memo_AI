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


def user_experience_context(request):
    """
    Exposes the signed-in user's experience preferences to every template so the
    shell can honour them server-side (before any JS runs):

    * ``reduce_motion``  — disables the app's decorative animations.
    * ``user_theme``     — the saved light/dark/system choice (initial paint).
    * ``face_recognition_unlocked`` — whether face features should appear at all.
    """
    defaults = {
        'reduce_motion': False,
        'user_theme': 'system',
        'face_recognition_unlocked': False,
        'user_preferences': None,
    }

    if not (hasattr(request, 'user') and request.user.is_authenticated):
        return defaults

    try:
        from .models import UserPreferences
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
    except Exception:
        return defaults

    return {
        'reduce_motion': bool(prefs.reduce_motion),
        'user_theme': prefs.theme or 'system',
        'face_recognition_unlocked': bool(prefs.face_recognition_consent),
        'user_preferences': prefs,
    }
