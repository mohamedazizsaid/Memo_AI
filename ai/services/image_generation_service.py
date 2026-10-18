"""
MemoAi — Image Generation Service
Coordinates Gemini (prompt generation) + Hugging Face (image generation) + Cloudinary (storage).
"""

import logging
import io
from django.conf import settings

logger = logging.getLogger('memoai')


def generate_entry_image(entry_id: str) -> str | None:
    """
    Full pipeline: entry → Gemini prompt → HF image → Cloudinary.
    
    Returns:
        str: Cloudinary URL of generated image, or None on failure
    """
    from journal.models import JournalEntry
    from media_app.models import Media

    try:
        entry = JournalEntry.objects.get(pk=entry_id)
    except JournalEntry.DoesNotExist:
        logger.error(f"Entry {entry_id} not found for image generation")
        return None

    if not entry.content:
        return None

    # Step 1: Generate image prompt via Gemini
    from .gemini_service import generate_image_prompt_from_entry
    image_prompt = generate_image_prompt_from_entry(entry.content)

    if not image_prompt:
        return None

    # Step 2: Generate image via HF
    from .huggingface_service import generate_image
    image_bytes = generate_image(image_prompt)

    if not image_bytes:
        return None

    # Step 3: Upload to Cloudinary
    try:
        import cloudinary.uploader
        result = cloudinary.uploader.upload(
            io.BytesIO(image_bytes),
            folder=f"memoai/{entry.user_id}/generated",
            resource_type='image',
            public_id=f"generated_{entry_id}",
            overwrite=True,
            format='webp',
            transformation=[
                {'quality': 'auto:good'},
                {'width': 768, 'crop': 'limit'},
            ]
        )
        cloudinary_url = result['secure_url']

        # Save generated image as media record
        Media.objects.update_or_create(
            entry=entry,
            media_type='GENERATED_IMAGE',
            defaults={
                'storage_url': cloudinary_url,
                'cloudinary_public_id': result['public_id'],
                'mime_type': 'image/webp',
                'processing_status': 'completed',
            }
        )

        # Update AI analysis with generated image URL
        from ai.models import AIAnalysis
        analysis, _ = AIAnalysis.objects.get_or_create(entry=entry)
        analysis.generated_image_url = cloudinary_url
        analysis.save(update_fields=['generated_image_url'])

        logger.info(f"Generated image for entry {entry_id}: {cloudinary_url}")
        return cloudinary_url

    except Exception as e:
        logger.error(f"Image generation Cloudinary upload failed: {e}", exc_info=True)
        return None
