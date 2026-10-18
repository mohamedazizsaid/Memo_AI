"""
MemoAi — Image Generation Service
Turns a journal entry into a real illustration using Pollinations (100% free,
key-less text-to-image). The rendered file is stored under MEDIA_ROOT and the
entry's AIAnalysis.generated_image_url is updated.

No mocking: if the provider is unreachable the task fails and the entry shows
a real error state.
"""

import logging
import os
import urllib.parse
import uuid

import requests
from django.conf import settings

logger = logging.getLogger('memoai')

DEFAULT_STYLE = (
    "artistic painterly illustration, warm light, soft pastel palette, "
    "personal memory, highly detailed, no text, no watermark"
)


def _build_image_url(prompt: str) -> str:
    base = getattr(settings, 'POLLINATIONS_BASE_URL', 'https://image.pollinations.ai/prompt')
    model = getattr(settings, 'IMAGE_GENERATION_MODEL', 'flux')
    width = getattr(settings, 'IMAGE_GENERATION_WIDTH', 896)
    height = getattr(settings, 'IMAGE_GENERATION_HEIGHT', 576)
    encoded = urllib.parse.quote(prompt.strip()[:900], safe='')
    query = urllib.parse.urlencode({
        'width': width,
        'height': height,
        'model': model,
        'nologo': 'true',
    })
    return f"{base}/{encoded}?{query}"


def generate_image_bytes(prompt: str, timeout: int = 120) -> bytes:
    """Fetch a generated image for ``prompt`` from the free provider."""
    if not prompt or not prompt.strip():
        return b''

    url = _build_image_url(prompt)
    logger.info("Requesting generated image from Pollinations")
    response = requests.get(
        url,
        timeout=timeout,
        headers={'User-Agent': 'MemoAI/1.0 (+journal-app)'},
        stream=True,
    )
    response.raise_for_status()

    content_type = (response.headers.get('Content-Type') or '').lower()
    if 'image' not in content_type:
        # The provider sometimes returns HTML/JSON while it warms up.
        raise RuntimeError(f"Unexpected content type from image provider: {content_type or 'unknown'}")

    buffer = bytearray()
    for chunk in response.iter_content(chunk_size=32768):
        if chunk:
            buffer.extend(chunk)
        if len(buffer) > 12 * 1024 * 1024:  # safety ceiling: 12 MB
            break

    if len(buffer) < 1024:
        raise RuntimeError("Image provider returned an empty payload.")
    return bytes(buffer)


def generate_entry_image(entry_id: str) -> str | None:
    """
    Full pipeline: entry → image prompt → Pollinations → local media.

    Returns the public URL of the generated image, or ``None`` on failure.
    """
    from journal.models import JournalEntry
    from media_app.models import Media
    from ai.models import AIAnalysis
    from ai.services.gemini_service import generate_image_prompt_from_entry

    try:
        entry = JournalEntry.objects.get(pk=entry_id)
    except JournalEntry.DoesNotExist:
        logger.error("Entry %s not found for image generation", entry_id)
        return None

    if not entry.content:
        return None

    analysis, _ = AIAnalysis.objects.get_or_create(entry=entry)

    # 1. Build the best prompt available.
    prompt = ''
    try:
        prompt = (entry.ai_analysis.image_prompt or '').strip()
    except Exception:
        prompt = ''
    if not prompt:
        try:
            prompt = generate_image_prompt_from_entry(entry.content)
        except Exception as exc:
            logger.warning("Gemini image prompt failed, using style fallback: %s", exc)
            prompt = f"An artistic illustration inspired by this day: {entry.content[:280]}"
    if DEFAULT_STYLE not in prompt:
        prompt = f"{prompt}. {DEFAULT_STYLE}"

    # 2. Render the image (free provider).
    try:
        image_bytes = generate_image_bytes(prompt)
    except Exception as exc:
        logger.error("Image rendering failed for entry %s: %s", entry_id, exc)
        analysis.image_generation_status = 'failed'
        analysis.save(update_fields=['image_generation_status'])
        return None

    # 3. Persist to MEDIA_ROOT.
    try:
        target_dir = settings.MEDIA_ROOT / 'generated' / str(entry.user_id)
        os.makedirs(target_dir, exist_ok=True)
        filename = f"entry_{entry_id}_{uuid.uuid4().hex[:8]}.jpg"
        with open(target_dir / filename, 'wb') as dest:
            dest.write(image_bytes)
        local_url = f"{settings.MEDIA_URL}generated/{entry.user_id}/{filename}"
    except Exception as exc:
        logger.error("Could not store generated image for %s: %s", entry_id, exc)
        analysis.image_generation_status = 'failed'
        analysis.save(update_fields=['image_generation_status'])
        return None

    # 4. Record it.
    Media.objects.update_or_create(
        entry=entry,
        media_type='GENERATED_IMAGE',
        defaults={
            'storage_url': local_url,
            'mime_type': 'image/jpeg',
            'file_size': len(image_bytes),
            'processing_status': 'completed',
        },
    )
    analysis.generated_image_url = local_url
    analysis.image_prompt = prompt
    analysis.image_generation_status = 'completed'
    analysis.save(update_fields=['generated_image_url', 'image_prompt', 'image_generation_status'])

    logger.info("Generated image for entry %s: %s", entry_id, local_url)
    return local_url
