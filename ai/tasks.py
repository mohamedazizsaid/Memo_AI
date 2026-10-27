"""
MemoAi — AI Celery Tasks
Asynchronous AI processing pipeline.
Each task fails independently — a failure doesn't block others.

No mock results are ever produced: when a provider is unavailable the affected
status becomes ``failed`` and the entry surfaces the real error state.
"""

import logging

from celery import shared_task
from django.utils import timezone

from ai.services import AIServiceError

logger = logging.getLogger('memoai')


def _prefs_for(user):
    try:
        from accounts.models import UserPreferences
        prefs, _ = UserPreferences.objects.get_or_create(user=user)
        return prefs
    except Exception:
        return None


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    name='ai.tasks.analyze_entry',
)
def analyze_entry(self, entry_id: str):
    """
    Main AI pipeline for a journal entry:
    sentiment + Gemini summary + keywords + (free) image generation.
    """
    from journal.models import JournalEntry
    from ai.models import AIAnalysis

    logger.info("Starting AI analysis for entry %s", entry_id)

    try:
        entry = JournalEntry.objects.get(pk=entry_id)
    except JournalEntry.DoesNotExist:
        logger.error("Entry %s not found", entry_id)
        return

    analysis, _ = AIAnalysis.objects.get_or_create(entry=entry)
    prefs = _prefs_for(entry.user)

    # ── Rate limit : 3 analyses AI / jour / user ─────────────────────────────
    try:
        from dashboard.models import AIUsageQuota
        quota, _ = AIUsageQuota.objects.get_or_create(user=entry.user)
        if not quota.can_analyze():
            logger.warning(
                "AI quota exceeded for user %s (daily_count=%d/%d) — skipping entry %s",
                entry.user.email, quota.daily_count, quota.DAILY_LIMIT, entry_id,
            )
            analysis.summary_status = 'skipped'
            analysis.sentiment_status = 'skipped'
            analysis.emotion_status = 'skipped'
            analysis.image_generation_status = 'skipped'
            analysis.save(update_fields=[
                'summary_status', 'sentiment_status',
                'emotion_status', 'image_generation_status',
            ])
            entry.ai_status = 'completed'
            entry.ai_error_message = (
                f"Quota AI atteint ({quota.daily_count}/{quota.DAILY_LIMIT} "
                f"analyses aujourd'hui). Réessayez demain."
            )
            entry.save(update_fields=['ai_status', 'ai_error_message'])
            return
        # Quota disponible — on l'incrémente avant le pipeline
        quota.increment()
    except Exception as quota_exc:
        # Si le module dashboard n'est pas encore disponible, on laisse passer
        logger.warning("Could not check AI quota for entry %s: %s", entry_id, quota_exc)

    content = (entry.content or '').strip()
    if not content:
        logger.info("Entry %s has no content — skipping text analysis", entry_id)
        analysis.summary_status = 'skipped'
        analysis.sentiment_status = 'skipped'
        analysis.save(update_fields=['summary_status', 'sentiment_status'])
        entry.ai_status = 'completed'
        entry.save(update_fields=['ai_status'])
        return

    try:
        lang = entry.user.preferences.language
    except Exception:
        lang = 'fr'

    summaries_enabled = getattr(prefs, 'ai_summaries_enabled', True)
    sentiment_enabled = getattr(prefs, 'sentiment_analysis_enabled', True)

    errors = []

    if summaries_enabled:
        # ── Gemini: summary + keywords + sentiment + image prompt ──────────
        try:
            from ai.services.gemini_service import summarize_entry
            result = summarize_entry(content, language=lang)

            analysis.summary = result.get('summary', '')
            analysis.keywords = result.get('keywords', [])
            analysis.mood_insight = result.get('mood_insight', '')
            analysis.image_prompt = result.get('image_prompt', '')
            analysis.summary_status = 'completed' if analysis.summary else 'failed'
            update_fields = ['summary', 'keywords', 'mood_insight', 'image_prompt', 'summary_status']

            if sentiment_enabled and result.get('sentiment'):
                analysis.sentiment = result['sentiment']
                analysis.sentiment_score = result.get('sentiment_score')
                analysis.sentiment_status = 'completed'
                update_fields += ['sentiment', 'sentiment_score', 'sentiment_status']
            elif not sentiment_enabled:
                analysis.sentiment_status = 'skipped'
                update_fields.append('sentiment_status')

            analysis.save(update_fields=update_fields)
            logger.info("Gemini analysis completed for %s", entry_id)
        except AIServiceError as exc:
            logger.error("Gemini analysis failed for %s: %s", entry_id, exc)
            analysis.summary_status = 'failed'
            fields = ['summary_status']
            if sentiment_enabled:
                analysis.sentiment_status = 'failed'
                fields.append('sentiment_status')
            analysis.save(update_fields=fields)
            errors.append(f"summary: {exc}")
    else:
        analysis.summary_status = 'skipped'
        analysis.save(update_fields=['summary_status'])

        # Sentiment can still be computed locally (no Gemini call needed).
        if sentiment_enabled:
            try:
                from ai.services.huggingface_service import analyze_sentiment
                s = analyze_sentiment(content)
                analysis.sentiment = s.get('sentiment', 'neutral')
                analysis.sentiment_score = s.get('score', 0.5)
                analysis.sentiment_status = 'completed'
                analysis.save(update_fields=['sentiment', 'sentiment_score', 'sentiment_status'])
            except Exception as exc:
                logger.error("Sentiment analysis failed for %s: %s", entry_id, exc)
                analysis.sentiment_status = 'failed'
                analysis.save(update_fields=['sentiment_status'])
                errors.append(f"sentiment: {exc}")
        else:
            analysis.sentiment_status = 'skipped'
            analysis.save(update_fields=['sentiment_status'])

    # ── 7-class Emotion Classification (French-emotion model) ───────────────
    try:
        from ai.services.emotion_service import classify_emotion
        emo_res = classify_emotion(content, lang=lang, user_mood=entry.mood)
        analysis.emotion = emo_res.get('emotion', 'neutre')
        analysis.emotion_score = emo_res.get('score', 0.5)
        analysis.emotion_status = 'completed'
        analysis.save(update_fields=['emotion', 'emotion_score', 'emotion_status'])
        logger.info("Emotion classification for %s: %s (score=%.2f)", entry_id, analysis.emotion, analysis.emotion_score or 0)
    except Exception as exc:
        logger.error("Emotion classification failed for %s: %s", entry_id, exc)
        analysis.emotion_status = 'failed'
        analysis.save(update_fields=['emotion_status'])

    # ── Free image generation ───────────────────────────────────────────────
    if getattr(prefs, 'image_generation_enabled', True):
        try:
            generate_entry_image_task.delay(entry_id)
        except Exception as exc:
            logger.warning("Could not trigger image generation for %s: %s", entry_id, exc)
    else:
        analysis.image_generation_status = 'skipped'
        analysis.save(update_fields=['image_generation_status'])

    entry.ai_status = 'failed' if errors else 'completed'
    entry.ai_error_message = '; '.join(errors)
    entry.save(update_fields=['ai_status', 'ai_error_message'])
    logger.info("AI analysis finished for entry %s (status=%s)", entry_id, entry.ai_status)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    name='ai.tasks.process_audio_media',
)
def process_audio_media(self, media_id: str):
    """Transcribe an audio media file with Gemini, then analyse the entry."""
    from media_app.models import Media
    from ai.models import AIAnalysis

    logger.info("Processing audio media %s", media_id)

    try:
        media = Media.objects.select_related('entry', 'entry__user').get(pk=media_id)
    except Media.DoesNotExist:
        logger.error("Media %s not found", media_id)
        return

    entry = media.entry
    analysis, _ = AIAnalysis.objects.get_or_create(entry=entry)

    # ── Téléchargement des bytes audio (utilisé à la fois pour la
    #    transcription et pour la détection émotionnelle vocale) ────────────────
    audio_bytes = None
    mime_type = media.mime_type or 'audio/mpeg'
    try:
        import requests as _req
        resp = _req.get(media.storage_url, timeout=60)
        resp.raise_for_status()
        audio_bytes = resp.content
        mime_type = resp.headers.get('Content-Type', mime_type).split(';')[0]
    except Exception as exc:
        logger.warning("Could not download audio bytes for %s: %s", media_id, exc)

    # ── Transcription ──────────────────────────────────────────────────────────
    try:
        from ai.services.huggingface_service import transcribe_audio
        result = transcribe_audio(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
        ) if audio_bytes else transcribe_audio(audio_url=media.storage_url, mime_type=mime_type)
        transcription = result.get('text', '')

        if transcription:
            analysis.transcription = transcription
            analysis.transcription_language = result.get('language', '')
            analysis.transcription_status = 'completed'
            analysis.save(update_fields=['transcription', 'transcription_language', 'transcription_status'])

            if not entry.content:
                entry.content = transcription
                entry.save(update_fields=['content'])
        else:
            analysis.transcription_status = 'skipped'
            analysis.save(update_fields=['transcription_status'])

        media.processing_status = 'completed'
        media.save(update_fields=['processing_status'])

    except Exception as exc:
        logger.error("Audio transcription failed for %s: %s", media_id, exc, exc_info=True)
        analysis.transcription_status = 'failed'
        analysis.save(update_fields=['transcription_status'])
        media.processing_status = 'failed'
        media.processing_error = str(exc)
        media.save(update_fields=['processing_status', 'processing_error'])

    # ── Détection des émotions vocales (complémentaire, non certaine) ──────────
    if audio_bytes:
        try:
            lang = 'fr'
            try:
                lang = entry.user.preferences.language
            except Exception:
                pass

            from ai.services.voice_emotion_service import classify_voice_emotion
            ve_result = classify_voice_emotion(
                audio_bytes=audio_bytes,
                mime_type=mime_type,
                lang=lang,
            )

            if ve_result.get('available') and ve_result.get('voice_emotion'):
                analysis.voice_emotion         = ve_result['voice_emotion']
                analysis.voice_emotion_score   = ve_result['voice_emotion_score']
                analysis.voice_emotion_uncertain = ve_result.get('uncertain', True)
                analysis.voice_emotion_status  = 'completed'
                analysis.save(update_fields=[
                    'voice_emotion', 'voice_emotion_score',
                    'voice_emotion_uncertain', 'voice_emotion_status',
                ])
                logger.info(
                    "Voice emotion for %s: %s (score=%.2f, uncertain=%s)",
                    media_id, analysis.voice_emotion,
                    analysis.voice_emotion_score or 0,
                    analysis.voice_emotion_uncertain,
                )
            else:
                # Modèle absent ou audio invalide → statut skipped, pas d'erreur bloquante
                analysis.voice_emotion_status = 'skipped'
                analysis.save(update_fields=['voice_emotion_status'])
                logger.info(
                    "Voice emotion skipped for %s: %s",
                    media_id, ve_result.get('reason', 'model unavailable')
                )
        except Exception as exc:
            logger.warning("Voice emotion detection failed for %s: %s", media_id, exc)
            analysis.voice_emotion_status = 'failed'
            analysis.save(update_fields=['voice_emotion_status'])
    else:
        analysis.voice_emotion_status = 'skipped'
        analysis.save(update_fields=['voice_emotion_status'])

    # ── Lancer l'analyse textuelle si une transcription est disponible ─────────
    if analysis.transcription:
        analyze_entry.delay(str(entry.id))




@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    name='ai.tasks.process_image_media',
)
def process_image_media(self, media_id: str, descriptors=None):
    """
    Detect faces in an image media file and match/create Person records.

    ``descriptors`` (optional) is a list of ``{'embedding': [...], 'box': {...}}``
    computed client-side with face-api.js. When absent we fall back to OpenCV
    bounding boxes (detection without identity).
    """
    from media_app.models import Media

    logger.info("Processing image media %s", media_id)

    try:
        media = Media.objects.select_related('entry', 'entry__user').get(pk=media_id)
    except Media.DoesNotExist:
        logger.error("Media %s not found", media_id)
        return

    user = media.entry.user
    prefs = _prefs_for(user)
    if prefs is not None and not prefs.face_recognition_consent:
        logger.info("Face recognition disabled for user %s", user.id)
        media.processing_status = 'completed'
        media.save(update_fields=['processing_status'])
        return

    try:
        from ai.services.face_recognition_service import (
            detect_faces, find_matching_person, embedding_to_db, db_to_embedding,
        )
        from persons.models import Person, FaceDetection
        import requests

        faces = descriptors or []
        if not faces:
            response = requests.get(media.storage_url, timeout=30)
            response.raise_for_status()
            faces = detect_faces(response.content)
            logger.info("Server-side detection found %d face(s) for media %s", len(faces), media_id)

        known_persons = list(
            Person.objects.filter(user=user, face_embedding__isnull=False)
            .exclude(face_embedding='').values('id', 'name', 'face_embedding')
        )
        for person in known_persons:
            person['embedding'] = db_to_embedding(person['face_embedding'])

        auto_delete = bool(getattr(prefs, 'auto_delete_face_embeddings', False))

        for face in faces:
            embedding = face.get('embedding')
            bounding_box = face.get('box') or face.get('bounding_box') or {}
            matched = find_matching_person(embedding, known_persons) if embedding else None

            if matched:
                person = Person.objects.get(pk=matched['id'])
                confidence = matched['confidence']
            elif embedding and not auto_delete:
                person = Person.objects.create(
                    user=user, name='Inconnu', face_embedding=embedding_to_db(embedding),
                )
                known_persons.append({'id': str(person.id), 'name': person.name, 'embedding': embedding})
                confidence = 1.0
            else:
                person = None
                confidence = face.get('confidence', 0.85)

            FaceDetection.objects.create(
                media=media, person=person, confidence=confidence, bounding_box=bounding_box,
            )

        media.processing_status = 'completed'
        media.save(update_fields=['processing_status'])
        logger.info("Face processing completed for media %s", media_id)

    except Exception as exc:
        logger.error("Image processing failed for %s: %s", media_id, exc, exc_info=True)
        media.processing_status = 'failed'
        media.processing_error = str(exc)
        media.save(update_fields=['processing_status', 'processing_error'])


@shared_task(name='ai.tasks.generate_entry_image_task')
def generate_entry_image_task(entry_id: str):
    """Generate a free AI illustration for a journal entry."""
    from ai.services.image_generation_service import generate_entry_image
    generate_entry_image(entry_id)


@shared_task(name='ai.tasks.cleanup_stale_tasks')
def cleanup_stale_tasks():
    """Mark AI analyses stuck in 'processing' for too long as failed."""
    from datetime import timedelta
    from journal.models import JournalEntry

    cutoff = timezone.now() - timedelta(hours=2)
    stale = JournalEntry.objects.filter(ai_status='processing', updated_at__lt=cutoff)
    count = stale.count()
    stale.update(ai_status='failed', ai_error_message='Task timed out')
    logger.info("Cleaned up %s stale AI tasks", count)
