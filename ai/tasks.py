"""
MemoAi — AI Celery Tasks
Asynchronous AI processing pipeline.
Each task fails independently — a failure doesn't block others.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('memoai')


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='ai.tasks.analyze_entry',
)
def analyze_entry(self, entry_id: str):
    """
    Main AI pipeline for a journal entry.
    Runs: sentiment analysis + Gemini summary + keywords + image generation.
    
    Audio transcription is handled separately via process_audio_media task.
    """
    from journal.models import JournalEntry
    from ai.models import AIAnalysis

    logger.info(f"Starting AI analysis for entry {entry_id}")

    try:
        entry = JournalEntry.objects.get(pk=entry_id)
    except JournalEntry.DoesNotExist:
        logger.error(f"Entry {entry_id} not found")
        return

    # Get or create AI analysis record
    analysis, _ = AIAnalysis.objects.get_or_create(entry=entry)

    content = entry.content
    if not content or not content.strip():
        logger.info(f"Entry {entry_id} has no content — skipping text analysis")
        analysis.summary_status = 'skipped'
        analysis.sentiment_status = 'skipped'
        analysis.save(update_fields=['summary_status', 'sentiment_status'])
        entry.ai_status = 'completed'
        entry.save(update_fields=['ai_status'])
        return

    # Get user preferences
    try:
        lang = entry.user.preferences.language
    except Exception:
        lang = 'fr'

    errors = []

    # ── Step 1: Sentiment Analysis ───────────────────────────────────────
    try:
        from ai.services.huggingface_service import analyze_sentiment
        sentiment_result = analyze_sentiment(content)

        analysis.sentiment = sentiment_result.get('sentiment', 'neutral')
        analysis.sentiment_score = sentiment_result.get('score', 0.5)
        analysis.sentiment_status = 'completed'
        analysis.save(update_fields=['sentiment', 'sentiment_score', 'sentiment_status'])
        logger.info(f"Sentiment for {entry_id}: {analysis.sentiment} ({analysis.sentiment_score})")

    except Exception as e:
        logger.error(f"Sentiment analysis failed for {entry_id}: {e}")
        analysis.sentiment_status = 'failed'
        analysis.save(update_fields=['sentiment_status'])
        errors.append(f"sentiment: {str(e)}")

    # ── Step 2: Gemini Summary + Keywords ───────────────────────────────
    try:
        from ai.services.gemini_service import summarize_entry
        gemini_result = summarize_entry(content, language=lang)

        analysis.summary = gemini_result.get('summary', '')
        analysis.keywords = gemini_result.get('keywords', [])
        analysis.mood_insight = gemini_result.get('mood_insight', '')
        analysis.summary_status = 'completed'
        analysis.save(update_fields=['summary', 'keywords', 'mood_insight', 'summary_status'])
        logger.info(f"Gemini summary completed for {entry_id}")

    except Exception as e:
        logger.error(f"Gemini summary failed for {entry_id}: {e}")
        analysis.summary_status = 'failed'
        analysis.save(update_fields=['summary_status'])
        errors.append(f"summary: {str(e)}")

    # ── Step 3: Image Generation (async sub-task) ────────────────────────
    try:
        prefs = entry.user.preferences
        if prefs.image_generation_enabled and prefs.ai_summaries_enabled:
            generate_entry_image_task.delay(entry_id)
    except Exception as e:
        logger.warning(f"Could not trigger image generation for {entry_id}: {e}")

    # ── Mark entry as completed ──────────────────────────────────────────
    entry.ai_status = 'completed' if not errors else 'completed'  # partial success is still "completed"
    if errors:
        entry.ai_error_message = '; '.join(errors)
    entry.save(update_fields=['ai_status', 'ai_error_message'])

    logger.info(f"AI analysis completed for entry {entry_id}")


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    name='ai.tasks.process_audio_media',
)
def process_audio_media(self, media_id: str):
    """
    Process an audio media file:
    1. Download from Cloudinary
    2. Transcribe via Whisper (HuggingFace)
    3. Run sentiment on transcription
    4. Run Gemini summary on transcription
    5. Store in AIAnalysis
    """
    from media_app.models import Media
    from ai.models import AIAnalysis

    logger.info(f"Processing audio media {media_id}")

    try:
        media = Media.objects.select_related('entry', 'entry__user').get(pk=media_id)
    except Media.DoesNotExist:
        logger.error(f"Media {media_id} not found")
        return

    entry = media.entry

    try:
        # Transcribe
        from ai.services.huggingface_service import transcribe_audio
        result = transcribe_audio(audio_url=media.storage_url)
        transcription = result.get('text', '')

        if not transcription:
            media.processing_status = 'completed'
            media.save(update_fields=['processing_status'])
            return

        # Save transcription
        analysis, _ = AIAnalysis.objects.get_or_create(entry=entry)
        analysis.transcription = transcription
        analysis.transcription_language = result.get('language', '')
        analysis.transcription_status = 'completed'
        analysis.save(update_fields=['transcription', 'transcription_language', 'transcription_status'])

        media.processing_status = 'completed'
        media.save(update_fields=['processing_status'])

        logger.info(f"Transcription completed for media {media_id}")

        # Trigger full text analysis on the transcription
        # If entry has no text content, use transcription as content
        if not entry.content:
            entry.content = transcription
            entry.save(update_fields=['content'])

        analyze_entry.delay(str(entry.id))

    except Exception as e:
        logger.error(f"Audio processing failed for {media_id}: {e}", exc_info=True)
        media.processing_status = 'failed'
        media.processing_error = str(e)
        media.save(update_fields=['processing_status', 'processing_error'])

        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            pass


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name='ai.tasks.process_image_media',
)
def process_image_media(self, media_id: str):
    """
    Process an image media file:
    1. Download image from Cloudinary
    2. Run face detection
    3. Match or create Person records
    4. Store FaceDetection records
    """
    from media_app.models import Media

    logger.info(f"Processing image media {media_id}")

    try:
        media = Media.objects.select_related('entry', 'entry__user').get(pk=media_id)
    except Media.DoesNotExist:
        logger.error(f"Media {media_id} not found")
        return

    user = media.entry.user

    # Check if user has granted face recognition consent
    try:
        if not user.preferences.face_recognition_consent:
            logger.info(f"Face recognition disabled for user {user.id}")
            media.processing_status = 'completed'
            media.save(update_fields=['processing_status'])
            return
    except Exception:
        media.processing_status = 'completed'
        media.save(update_fields=['processing_status'])
        return

    try:
        from ai.services.face_recognition_service import detect_faces, find_matching_person, db_to_embedding
        from persons.models import Person, FaceDetection

        # Download image
        import requests
        response = requests.get(media.storage_url, timeout=30)
        response.raise_for_status()
        image_bytes = response.content

        # Detect faces
        faces = detect_faces(image_bytes)
        logger.info(f"Detected {len(faces)} face(s) in media {media_id}")

        # Get all known persons for this user (with embeddings)
        known_persons = list(
            Person.objects.filter(user=user, face_embedding__isnull=False)
            .values('id', 'name', 'face_embedding')
        )

        # Convert DB embeddings to lists
        for person in known_persons:
            if isinstance(person['face_embedding'], str):
                from ai.services.face_recognition_service import db_to_embedding
                person['embedding'] = db_to_embedding(person['face_embedding'])
            else:
                person['embedding'] = person['face_embedding'] or []

        for face_data in faces:
            embedding = face_data['embedding']
            bounding_box = face_data['bounding_box']

            # Try to match with known person
            matched = find_matching_person(embedding, known_persons)

            if matched:
                person = Person.objects.get(pk=matched['id'])
                confidence = matched['confidence']
            else:
                # Create new unknown person
                from ai.services.face_recognition_service import embedding_to_db
                person = Person.objects.create(
                    user=user,
                    name='Unknown',
                    face_embedding=embedding_to_db(embedding),
                )
                known_persons.append({
                    'id': str(person.id),
                    'name': person.name,
                    'embedding': embedding,
                })
                confidence = 1.0

            # Record detection
            FaceDetection.objects.create(
                media=media,
                person=person,
                confidence=confidence,
                bounding_box=bounding_box,
            )

        media.processing_status = 'completed'
        media.save(update_fields=['processing_status'])
        logger.info(f"Face detection completed for media {media_id}")

    except Exception as e:
        logger.error(f"Image processing failed for {media_id}: {e}", exc_info=True)
        media.processing_status = 'failed'
        media.processing_error = str(e)
        media.save(update_fields=['processing_status', 'processing_error'])

        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            pass


@shared_task(name='ai.tasks.generate_entry_image_task')
def generate_entry_image_task(entry_id: str):
    """Generate an AI illustration for a journal entry."""
    from ai.services.image_generation_service import generate_entry_image
    generate_entry_image(entry_id)


@shared_task(name='ai.tasks.cleanup_stale_tasks')
def cleanup_stale_tasks():
    """
    Clean up AI analyses that have been stuck in 'processing' state for too long.
    Runs every 6 hours via Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta
    from journal.models import JournalEntry

    cutoff = timezone.now() - timedelta(hours=2)
    stale = JournalEntry.objects.filter(
        ai_status='processing',
        updated_at__lt=cutoff
    )
    count = stale.count()
    stale.update(ai_status='failed', ai_error_message='Task timed out')
    logger.info(f"Cleaned up {count} stale AI tasks")
