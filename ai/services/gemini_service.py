"""
MemoAi — Gemini Service
Real AI text generation: summaries, keywords, sentiment and image prompts.

There is deliberately NO mock fallback here. If the provider is unavailable or
returns something we cannot parse, an ``AIServiceError`` is raised so the entry
is honestly marked as ``failed`` instead of showing fabricated analysis.
"""

import json
import logging

from django.conf import settings

from . import AIServiceError

logger = logging.getLogger('memoai')

# Lazy import — only loaded when needed
_gemini_client = None
_gemini_model_name = None

# The JSON contract we ask Gemini to honour.
_RESPONSE_SCHEMA_HINT = """{
    "summary": "Résumé empathique de 2 à 3 phrases",
    "keywords": ["mot1", "mot2", "mot3", "mot4", "mot5"],
    "sentiment": "positive | neutral | negative",
    "sentiment_score": 0.0,
    "mood_insight": "Une phrase bienveillante sur l'état émotionnel détecté",
    "image_prompt": "A detailed English prompt for an image generation model that visually captures this entry, warm and personal, painterly style"
}"""


def _get_client():
    """Get or create the Gemini model client (singleton)."""
    global _gemini_client, _gemini_model_name

    if not settings.GEMINI_API_KEY:
        raise AIServiceError(
            "GEMINI_API_KEY is not configured. Add it to your .env to enable AI analysis."
        )

    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash')
    if _gemini_client is not None and _gemini_model_name == model_name:
        return _gemini_client

    try:
        import google.generativeai as genai
    except ImportError as exc:  # pragma: no cover - dependency issue
        raise AIServiceError(
            "google-generativeai is not installed. Run: pip install google-generativeai"
        ) from exc

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_client = genai.GenerativeModel(model_name)
        _gemini_model_name = model_name
    except Exception as exc:  # pragma: no cover - config issue
        raise AIServiceError(f"Gemini client initialization failed: {exc}") from exc

    return _gemini_client


def _strip_code_fence(text: str) -> str:
    text = (text or '').strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.lower().startswith('json'):
            text = text[4:]
        text = text.strip()
    return text


def _normalise_sentiment(value) -> str:
    value = str(value or '').strip().lower()
    if value in ('positive', 'pos', 'happy', 'joyful'):
        return 'positive'
    if value in ('negative', 'neg', 'sad', 'unhappy'):
        return 'negative'
    return 'neutral'


def summarize_entry(content: str, language: str = 'fr') -> dict:
    """
    Analyse a journal entry with Gemini.

    Returns a dict with ``summary``, ``keywords``, ``mood_insight``,
    ``sentiment``, ``sentiment_score`` and ``image_prompt``.
    Raises ``AIServiceError`` when the model cannot be reached or parsed.
    """
    if not content or not content.strip():
        return {}

    client = _get_client()

    lang_instruction = "en français" if language == 'fr' else "in English"

    prompt = f"""Tu es un assistant personnel bienveillant qui analyse des entrées de journal intime.

Analyse l'entrée ci-dessous et réponds UNIQUEMENT avec un JSON valide (aucun markdown, aucun commentaire).

Tous les champs textuels destinés à l'utilisateur ("summary", "keywords", "mood_insight") doivent être écrits {lang_instruction}.
Le champ "image_prompt" doit rester en anglais.

Schéma exact attendu :
{_RESPONSE_SCHEMA_HINT}

ENTRÉE:
{content[:3000]}
"""

    try:
        response = client.generate_content(
            prompt,
            generation_config={
                'response_mime_type': 'application/json',
                'temperature': 0.7,
            },
        )
    except Exception as exc:
        logger.error("Gemini generate_content failed: %s", exc)
        raise AIServiceError(f"Gemini request failed: {exc}") from exc

    raw = _strip_code_fence(getattr(response, 'text', '') or '')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Gemini JSON parse error: %s — raw: %s", exc, raw[:200])
        raise AIServiceError("Gemini returned an unreadable answer.") from exc

    keywords = data.get('keywords') or []
    if not isinstance(keywords, list):
        keywords = [str(keywords)]

    try:
        score = float(data.get('sentiment_score') or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(1.0, score))

    return {
        'summary': (data.get('summary') or '').strip(),
        'keywords': [str(k).strip() for k in keywords if str(k).strip()][:10],
        'mood_insight': (data.get('mood_insight') or '').strip(),
        'sentiment': _normalise_sentiment(data.get('sentiment')),
        'sentiment_score': score,
        'image_prompt': (data.get('image_prompt') or '').strip(),
    }


def generate_daily_insight(entries: list, language: str = 'fr') -> str:
    """Generate a daily narrative insight from several entries."""
    if not entries:
        return ""

    client = _get_client()
    combined = "\n\n".join(
        f"Entry {i + 1} ({e.get('date', '')}):\n{e.get('content', '')[:500]}"
        for i, e in enumerate(entries[:5])
    )

    lang_instruction = "en français" if language == 'fr' else "in English"
    prompt = f"""Génère un résumé narratif et bienveillant de cette journée à partir de ces entrées de journal.
Ton doux, empathique et personnel. 2 à 3 paragraphes {lang_instruction}.

ENTRÉES:
{combined}
"""

    try:
        response = client.generate_content(prompt)
        return (response.text or '').strip()
    except Exception as exc:
        logger.error("Gemini daily insight error: %s", exc)
        raise AIServiceError(f"Gemini request failed: {exc}") from exc


def generate_weekly_summary(week_data: dict, language: str = 'fr') -> str:
    """Generate a weekly summary with mood trends and highlights."""
    client = _get_client()
    lang_instruction = "en français" if language == 'fr' else "in English"

    prompt = f"""Génère un résumé hebdomadaire bienveillant basé sur ces données de journal :

Nombre d'entrées : {week_data.get('total_entries', 0)}
Humeur dominante : {week_data.get('dominant_mood') or 'inconnue'}
Mots-clés fréquents : {', '.join(week_data.get('top_keywords', []) or [])}
Lieux visités : {', '.join(week_data.get('locations', []) or [])}

Rédige un résumé chaleureux et personnel en 2 à 3 phrases {lang_instruction}.
"""

    try:
        response = client.generate_content(prompt)
        return (response.text or '').strip()
    except Exception as exc:
        logger.error("Gemini weekly summary error: %s", exc)
        raise AIServiceError(f"Gemini request failed: {exc}") from exc


def generate_image_prompt_from_entry(content: str) -> str:
    """Generate an optimised English image-generation prompt from entry content."""
    client = _get_client()
    prompt = f"""Based on this journal entry, write ONE detailed image generation prompt.
The image should be artistic, personal, warm and painterly — not literal.
Reply with the prompt text only, nothing else (max 60 words).

Journal entry:
{content[:1000]}
"""

    try:
        response = client.generate_content(prompt)
        return (response.text or '').strip()[:500]
    except Exception as exc:
        logger.error("Gemini image prompt error: %s", exc)
        raise AIServiceError(f"Gemini request failed: {exc}") from exc
