"""
MemoAi — Gemini Service
AI-powered text generation: summaries, keywords, image prompts.
All Gemini API calls go through this service.
"""

import logging
import json
from django.conf import settings

logger = logging.getLogger('memoai')

# Lazy import — only loaded when needed
_gemini_client = None


def _get_client():
    """Get or create Gemini client."""
    global _gemini_client
    if _gemini_client is None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            _gemini_client = genai.GenerativeModel(settings.GEMINI_MODEL)
        except ImportError:
            logger.error("google-generativeai not installed. Run: pip install google-generativeai")
            return None
        except Exception as e:
            logger.error(f"Gemini client initialization failed: {e}")
            return None
    return _gemini_client


def _mock_response(entry_content):
    """Return a mock response when AI is unavailable (test/dev mode)."""
    words = entry_content.split()[:10]
    return {
        'summary': f"[Mock Summary] A thoughtful entry about {' '.join(words[:5])}...",
        'keywords': ['memory', 'journal', 'reflection', 'day', 'experience'],
        'image_prompt': f"A serene, artistic illustration of a personal moment, warm pastel colors, soft light",
        'mood_insight': "This entry reflects a moment of personal reflection.",
    }


def summarize_entry(content: str, language: str = 'fr') -> dict:
    """
    Generate a summary of a journal entry.
    
    Returns:
        dict with 'summary', 'keywords', 'image_prompt', 'mood_insight'
    """
    if not content or not content.strip():
        return {}

    if settings.AI_MOCK_MODE or not settings.GEMINI_API_KEY:
        logger.info("Gemini: using mock mode")
        return _mock_response(content)

    client = _get_client()
    if not client:
        return _mock_response(content)

    lang_instruction = "en français" if language == 'fr' else "in English"

    prompt = f"""
Tu es un assistant personnel bienveillant qui analyse des entrées de journal intime.

Analyse cette entrée de journal et fournis une réponse JSON structurée.

ENTRÉE:
{content[:3000]}

Réponds UNIQUEMENT avec un JSON valide (pas de markdown, pas de code block) dans ce format exact:
{{
    "summary": "Un résumé empathique de 2-3 phrases {lang_instruction}",
    "keywords": ["mot1", "mot2", "mot3", "mot4", "mot5"],
    "image_prompt": "A detailed prompt for an image generation AI, describing a visual scene that captures the essence of this journal entry, warm and personal, artistic style",
    "mood_insight": "Une observation bienveillante sur l'état émotionnel détecté, 1 phrase {lang_instruction}"
}}
"""

    try:
        response = client.generate_content(prompt)
        text = response.text.strip()

        # Clean potential markdown code blocks
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
            text = text.strip()

        data = json.loads(text)
        return {
            'summary': data.get('summary', ''),
            'keywords': data.get('keywords', [])[:10],
            'image_prompt': data.get('image_prompt', ''),
            'mood_insight': data.get('mood_insight', ''),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Gemini JSON parse error: {e}, response: {response.text[:200]}")
        return _mock_response(content)
    except Exception as e:
        logger.error(f"Gemini summarize_entry error: {e}", exc_info=True)
        return _mock_response(content)


def generate_daily_insight(entries: list, language: str = 'fr') -> str:
    """
    Generate a daily insight/narrative from multiple entries.
    """
    if not entries:
        return ""

    if settings.AI_MOCK_MODE or not settings.GEMINI_API_KEY:
        return "[Mock] A beautiful day full of memories and reflections."

    client = _get_client()
    if not client:
        return ""

    combined = "\n\n".join([
        f"Entry {i+1} ({e.get('date', '')}):\n{e.get('content', '')[:500]}"
        for i, e in enumerate(entries[:5])
    ])

    lang_instruction = "en français" if language == 'fr' else "in English"
    prompt = f"""
Génère un résumé narratif et bienveillant de cette journée basé sur ces entrées de journal.
Le ton doit être doux, empathique et personnel. 2-3 paragraphes {lang_instruction}.

ENTRÉES:
{combined}
"""

    try:
        response = client.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini daily insight error: {e}")
        return ""


def generate_weekly_summary(week_data: dict, language: str = 'fr') -> str:
    """
    Generate a weekly summary with mood trends and highlights.
    """
    if settings.AI_MOCK_MODE or not settings.GEMINI_API_KEY:
        return "[Mock] A wonderful week with varied emotions and memorable moments."

    client = _get_client()
    if not client:
        return ""

    lang_instruction = "en français" if language == 'fr' else "in English"
    prompt = f"""
Génère un résumé hebdomadaire bienveillant basé sur ces données de journal:

Nombre d'entrées: {week_data.get('total_entries', 0)}
Humeur dominante: {week_data.get('dominant_mood', 'inconnue')}
Mots-clés fréquents: {', '.join(week_data.get('top_keywords', []))}
Lieux visités: {', '.join(week_data.get('locations', []))}

Rédige un résumé chaleureux et personnel en 2-3 phrases {lang_instruction}.
"""

    try:
        response = client.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini weekly summary error: {e}")
        return ""


def generate_image_prompt_from_entry(content: str) -> str:
    """
    Generate an optimized image generation prompt from entry content.
    """
    if settings.AI_MOCK_MODE or not settings.GEMINI_API_KEY:
        return "A serene landscape at golden hour, soft pastel colors, watercolor style, peaceful atmosphere"

    client = _get_client()
    if not client:
        return "A peaceful personal moment, soft colors, artistic illustration"

    prompt = f"""
Based on this journal entry, create a single detailed image generation prompt.
The image should be: artistic, personal, warm, not literal, in a painterly or illustrative style.
Return ONLY the image prompt text, nothing else.

Journal entry:
{content[:1000]}
"""

    try:
        response = client.generate_content(prompt)
        return response.text.strip()[:500]
    except Exception as e:
        logger.error(f"Gemini image prompt error: {e}")
        return "A peaceful personal moment, soft watercolor illustration, warm tones"
