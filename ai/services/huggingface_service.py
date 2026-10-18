"""
MemoAi — Sentiment, transcription & image helpers.

Hugging Face's inference host is no longer reachable, so this module no longer
depends on it:

* ``analyze_sentiment`` uses the HF endpoint only if it answers, and otherwise
  falls back to a real, deterministic bilingual (FR/EN) lexicon analyser —
  never to a fabricated constant.
* ``transcribe_audio`` uses Gemini (multimodal) for real transcription.
* ``generate_image`` is delegated to the free Pollinations image service.
"""

import io
import logging
import re

import requests
from django.conf import settings

from . import AIServiceError

logger = logging.getLogger('memoai')

HF_API_BASE = "https://api-inference.huggingface.co/models"


def _hf_headers():
    return {
        "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json",
    }


def _hf_available():
    return bool(settings.HUGGINGFACE_API_KEY)


# ─────────────────────────────────────────────
# Audio transcription (Gemini multimodal)
# ─────────────────────────────────────────────

def transcribe_audio(audio_url: str = None, audio_bytes: bytes = None, mime_type: str = 'audio/mpeg') -> dict:
    """Transcribe audio with Gemini. Returns {'text', 'language'}."""
    if audio_url and not audio_bytes:
        try:
            resp = requests.get(audio_url, timeout=60)
            resp.raise_for_status()
            audio_bytes = resp.content
            mime_type = resp.headers.get('Content-Type', mime_type).split(';')[0]
        except Exception as exc:
            raise AIServiceError(f"Could not download audio: {exc}") from exc

    if not audio_bytes:
        return {'text': '', 'language': ''}

    try:
        import google.generativeai as genai
    except ImportError as exc:  # pragma: no cover
        raise AIServiceError("google-generativeai is not installed.") from exc

    if not settings.GEMINI_API_KEY:
        raise AIServiceError("GEMINI_API_KEY is not configured.")

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(getattr(settings, 'GEMINI_VISION_MODEL', 'gemini-2.5-flash'))
        response = model.generate_content([
            "Transcris fidèlement cet enregistrement audio. Réponds uniquement avec "
            "le texte transcrit, sans commentaire. Termine par une ligne "
            "'LANGUE: <code>' avec le code de la langue détectée.",
            {'mime_type': mime_type, 'data': audio_bytes},
        ])
        text = (response.text or '').strip()
    except Exception as exc:
        logger.error("Gemini transcription failed: %s", exc)
        raise AIServiceError(f"Transcription failed: {exc}") from exc

    language = ''
    match = re.search(r'LANGUE:\s*([a-zA-Z\-]{2,10})\s*$', text)
    if match:
        language = match.group(1).lower()
        text = text[:match.start()].strip()
    return {'text': text, 'language': language}


# ─────────────────────────────────────────────
# Sentiment analysis (HF → local lexicon)
# ─────────────────────────────────────────────

SENTIMENT_LABELS = {
    'POSITIVE': 'positive',
    'NEGATIVE': 'negative',
    'NEUTRAL': 'neutral',
    'LABEL_0': 'negative',
    'LABEL_1': 'neutral',
    'LABEL_2': 'positive',
}

_POSITIVE_WORDS = {
    'happy', 'joy', 'joyful', 'great', 'amazing', 'wonderful', 'love', 'loved',
    'beautiful', 'grateful', 'thankful', 'excited', 'proud', 'calm', 'peaceful',
    'fun', 'smile', 'laughter', 'success', 'win', 'good', 'best', 'fantastic',
    'content', 'relaxed', 'hopeful', 'delighted', 'warm', 'brilliant', 'lovely',
    'heureux', 'heureuse', 'joie', 'magnifique', 'merveilleux', 'amour', 'aimé',
    'aimée', 'belle', 'beau', 'reconnaissant', 'reconnaissante', 'fier', 'fière',
    'calme', 'paisible', 'sourire', 'rire', 'réussi', 'réussite', 'bien', 'super',
    'génial', 'formidable', 'content', 'contente', 'détendu', 'chaleureux', 'bravo',
    'gratitude', 'excellent', 'plaisir', 'serein', 'sereine', 'sérénité', 'espoir',
}

_NEGATIVE_WORDS = {
    'sad', 'unhappy', 'angry', 'tired', 'exhausted', 'stressed', 'anxious',
    'worried', 'afraid', 'fear', 'lonely', 'depressed', 'terrible', 'awful',
    'bad', 'worse', 'worst', 'hate', 'pain', 'hurt', 'cry', 'crying', 'failed',
    'failure', 'problem', 'problems', 'difficult', 'hard', 'sick', 'ill', 'sorry',
    'triste', 'fatigué', 'fatiguée', 'fatigue', 'stressé', 'stressée', 'anxieux',
    'anxieuse', 'inquiet', 'inquiète', 'peur', 'seul', 'seule', 'déprimé',
    'déprimée', 'terrible', 'affreux', 'mauvais', 'pire', 'déteste', 'douleur',
    'mal', 'pleure', 'pleurer', 'échoué', 'échec', 'problème', 'problèmes',
    'difficile', 'dur', 'dure', 'malade', 'désolé', 'désolée', 'colère', 'énervé',
}

_NEGATORS = {'not', 'no', 'never', "don't", 'ne', 'pas', 'jamais', 'aucun', 'plus'}


def _lexicon_sentiment(text: str) -> dict:
    """Deterministic bilingual lexicon sentiment (real computation, no mock)."""
    tokens = re.findall(r"[a-zA-ZÀ-ÿ']+", (text or '').lower())
    if not tokens:
        return {'sentiment': 'neutral', 'score': 0.5, 'raw': []}

    pos = neg = 0
    for i, tok in enumerate(tokens):
        negated = i > 0 and tokens[i - 1] in _NEGATORS
        if tok in _POSITIVE_WORDS:
            neg += 1 if negated else 0
            pos += 0 if negated else 1
        elif tok in _NEGATIVE_WORDS:
            pos += 1 if negated else 0
            neg += 0 if negated else 1

    total = pos + neg
    if total == 0:
        return {'sentiment': 'neutral', 'score': 0.5, 'raw': [{'label': 'neutral', 'score': 0.5}]}

    raw_score = (pos - neg) / total  # -1 .. 1
    if raw_score > 0.15:
        sentiment = 'positive'
    elif raw_score < -0.15:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'
    score = round((raw_score + 1) / 2, 4)  # 0 .. 1, 0.5 == neutral
    return {
        'sentiment': sentiment,
        'score': score,
        'raw': [{'label': sentiment, 'score': score}],
    }


def analyze_sentiment(text: str) -> dict:
    """Analyse sentiment. Prefers Hugging Face, falls back to the local lexicon."""
    if not text or len(text.strip()) < 3:
        return {'sentiment': 'neutral', 'score': 0.5, 'raw': []}

    if _hf_available():
        try:
            model = settings.HUGGINGFACE_SENTIMENT_MODEL
            response = requests.post(
                f"{HF_API_BASE}/{model}",
                headers=_hf_headers(),
                json={"inputs": text[:2000]},
                timeout=20,
            )
            if response.status_code != 503:
                response.raise_for_status()
                result = response.json()
                if isinstance(result, list) and result and isinstance(result[0], list):
                    result = result[0]
                if result:
                    top = max(result, key=lambda x: x.get('score', 0))
                    sentiment = SENTIMENT_LABELS.get(str(top.get('label', '')).upper(), 'neutral')
                    return {'sentiment': sentiment, 'score': round(top.get('score', 0.5), 4), 'raw': result}
        except Exception as exc:
            logger.info("HuggingFace sentiment unavailable, using local lexicon: %s", exc)

    return _lexicon_sentiment(text)


# ─────────────────────────────────────────────
# Image generation (delegated to free provider)
# ─────────────────────────────────────────────

def generate_image(prompt: str) -> bytes:
    """Generate an image via the free Pollinations service."""
    from .image_generation_service import generate_image_bytes
    return generate_image_bytes(prompt)
