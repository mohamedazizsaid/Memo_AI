"""
MemoAi — Hugging Face Service
Audio transcription, sentiment analysis, and image generation via HF Inference API.
All Hugging Face API calls go through this service.
"""

import io
import logging
import base64
import requests
from django.conf import settings

logger = logging.getLogger('memoai')

HF_API_BASE = "https://api-inference.huggingface.co/models"


def _get_headers():
    return {
        "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json",
    }


def _is_available():
    return bool(settings.HUGGINGFACE_API_KEY) and not settings.AI_MOCK_MODE


# ─────────────────────────────────────────────
# Audio Transcription (Whisper)
# ─────────────────────────────────────────────

def transcribe_audio(audio_url: str = None, audio_bytes: bytes = None) -> dict:
    """
    Transcribe audio using Whisper via Hugging Face Inference API.
    
    Args:
        audio_url: URL of audio file (will be downloaded)
        audio_bytes: Raw audio bytes
        
    Returns:
        dict with 'text' (transcription) and 'language'
    """
    if settings.AI_MOCK_MODE or not settings.HUGGINGFACE_API_KEY:
        logger.info("HuggingFace: using mock transcription")
        return {
            'text': '[Mock Transcription] This is a simulated transcription of your audio recording. The voice journal feature will transcribe your real recordings when configured with a valid Hugging Face API key.',
            'language': 'fr',
        }

    try:
        # Download audio if URL provided
        if audio_url and not audio_bytes:
            response = requests.get(audio_url, timeout=30)
            response.raise_for_status()
            audio_bytes = response.content

        if not audio_bytes:
            return {'text': '', 'language': ''}

        # Send to Whisper
        model = settings.HUGGINGFACE_ASR_MODEL
        api_url = f"{HF_API_BASE}/{model}"

        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
                "Content-Type": "audio/wav",
            },
            data=audio_bytes,
            timeout=120,
        )

        if response.status_code == 503:
            # Model loading — retry after delay
            logger.warning("HuggingFace Whisper model loading, will retry")
            return {'text': '', 'language': '', 'status': 'loading'}

        response.raise_for_status()
        result = response.json()

        return {
            'text': result.get('text', ''),
            'language': result.get('chunks', [{}])[0].get('language', '') if result.get('chunks') else '',
        }

    except requests.RequestException as e:
        logger.error(f"HuggingFace transcription error: {e}")
        return {'text': '', 'language': '', 'error': str(e)}
    except Exception as e:
        logger.error(f"Transcription unexpected error: {e}", exc_info=True)
        return {'text': '', 'language': '', 'error': str(e)}


# ─────────────────────────────────────────────
# Sentiment Analysis
# ─────────────────────────────────────────────

SENTIMENT_LABELS = {
    'POSITIVE': 'positive',
    'NEGATIVE': 'negative',
    'NEUTRAL': 'neutral',
    'LABEL_0': 'negative',  # cardiffnlp labels
    'LABEL_1': 'neutral',
    'LABEL_2': 'positive',
}


def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment of text using Hugging Face.
    
    Returns:
        dict with 'sentiment' (positive/neutral/negative), 'score' (0-1), 'raw'
    """
    if settings.AI_MOCK_MODE or not settings.HUGGINGFACE_API_KEY:
        logger.info("HuggingFace: using mock sentiment")
        return {
            'sentiment': 'positive',
            'score': 0.72,
            'raw': [{'label': 'positive', 'score': 0.72}],
        }

    if not text or len(text.strip()) < 10:
        return {'sentiment': 'neutral', 'score': 0.5, 'raw': []}

    try:
        # Truncate to model max length (512 tokens ≈ 2000 chars)
        text_truncated = text[:2000]

        model = settings.HUGGINGFACE_SENTIMENT_MODEL
        api_url = f"{HF_API_BASE}/{model}"

        response = requests.post(
            api_url,
            headers=_get_headers(),
            json={"inputs": text_truncated},
            timeout=30,
        )

        if response.status_code == 503:
            return {'sentiment': 'neutral', 'score': 0.5, 'status': 'loading', 'raw': []}

        response.raise_for_status()
        result = response.json()

        # Handle nested list format [[{label, score}, ...]]
        if isinstance(result, list) and result and isinstance(result[0], list):
            result = result[0]

        # Find highest score
        if result:
            top = max(result, key=lambda x: x.get('score', 0))
            raw_label = top.get('label', 'NEUTRAL').upper()
            sentiment = SENTIMENT_LABELS.get(raw_label, 'neutral')
            score = round(top.get('score', 0.5), 4)
        else:
            sentiment, score = 'neutral', 0.5

        return {
            'sentiment': sentiment,
            'score': score,
            'raw': result,
        }

    except requests.RequestException as e:
        logger.error(f"HuggingFace sentiment error: {e}")
        return {'sentiment': 'neutral', 'score': 0.5, 'error': str(e), 'raw': []}
    except Exception as e:
        logger.error(f"Sentiment unexpected error: {e}", exc_info=True)
        return {'sentiment': 'neutral', 'score': 0.5, 'error': str(e), 'raw': []}


# ─────────────────────────────────────────────
# Image Generation (Stable Diffusion)
# ─────────────────────────────────────────────

def generate_image(prompt: str) -> bytes:
    """
    Generate an image using Stable Diffusion via Hugging Face.
    
    Returns:
        bytes: PNG image data, or None on failure
    """
    if settings.AI_MOCK_MODE or not settings.HUGGINGFACE_API_KEY:
        logger.info("HuggingFace: using mock image generation")
        return None  # No mock image bytes in dev mode

    try:
        model = settings.HUGGINGFACE_IMAGE_MODEL
        api_url = f"{HF_API_BASE}/{model}"

        # Add quality enhancers to prompt
        enhanced_prompt = f"{prompt}, high quality, artistic, detailed, warm colors, personal memory"
        negative_prompt = "ugly, blurry, low quality, nsfw, violence, text, watermark"

        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "inputs": enhanced_prompt,
                "parameters": {
                    "negative_prompt": negative_prompt,
                    "num_inference_steps": 30,
                    "guidance_scale": 7.5,
                    "width": 768,
                    "height": 512,
                }
            },
            timeout=120,
        )

        if response.status_code == 503:
            logger.warning("HuggingFace image model loading")
            return None

        response.raise_for_status()

        # Response is raw image bytes
        return response.content

    except requests.RequestException as e:
        logger.error(f"HuggingFace image generation error: {e}")
        return None
    except Exception as e:
        logger.error(f"Image generation unexpected error: {e}", exc_info=True)
        return None
