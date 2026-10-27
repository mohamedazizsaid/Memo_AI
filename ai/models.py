"""
MemoAi — AI Analysis Model
Stores results of all AI processing for a journal entry.
"""

import uuid
from django.db import models
from common.models import TimeStampedModel


class AIAnalysis(TimeStampedModel):
    """
    One-to-one with JournalEntry, stores all AI processing results.
    Each field is populated independently — a failure in one doesn't block others.
    """
    entry = models.OneToOneField(
        'journal.JournalEntry',
        on_delete=models.CASCADE,
        related_name='ai_analysis',
    )

    # Audio transcription (from Whisper)
    transcription = models.TextField(blank=True)
    transcription_language = models.CharField(max_length=10, blank=True)
    transcription_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('skipped', 'Skipped')],
        default='pending'
    )

    # Text analysis (from Gemini)
    summary = models.TextField(blank=True)
    keywords = models.JSONField(default=list, blank=True)
    mood_insight = models.TextField(blank=True)
    summary_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('skipped', 'Skipped')],
        default='pending'
    )

    # Sentiment (from Hugging Face)
    sentiment = models.CharField(max_length=20, blank=True)  # positive/neutral/negative
    sentiment_score = models.FloatField(null=True, blank=True)
    sentiment_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('skipped', 'Skipped')],
        default='pending'
    )

    # Emotion classification (French-emotion 7 classes: joie, tristesse, colere, peur, surprise, degout, neutre)
    emotion = models.CharField(max_length=30, blank=True)
    emotion_score = models.FloatField(null=True, blank=True)
    emotion_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('skipped', 'Skipped')],
        default='pending'
    )

    # Voice emotion (détection émotionnelle sur la voix — estimation complémentaire non certaine)
    voice_emotion = models.CharField(max_length=30, blank=True)
    voice_emotion_score = models.FloatField(null=True, blank=True)
    voice_emotion_uncertain = models.BooleanField(default=True)
    voice_emotion_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('skipped', 'Skipped')],
        default='pending'
    )

    # Generated image URL (from Pollinations + local media)
    generated_image_url = models.CharField(max_length=1000, blank=True)
    image_prompt = models.TextField(blank=True)
    image_generation_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('skipped', 'Skipped')],
        default='pending'
    )

    class Meta:
        db_table = 'ai_analysis'
        verbose_name = 'AI Analysis'
        verbose_name_plural = 'AI Analyses'

    def __str__(self):
        return f"AIAnalysis(entry={self.entry_id})"

    @property
    def emotion_data(self):
        from ai.services.emotion_service import get_emotion_meta
        return get_emotion_meta(self.emotion)

    @property
    def emotion_label(self):
        return self.emotion_data.get('label', self.emotion.title() if self.emotion else '')

    @property
    def emotion_emoji(self):
        from common.icons import get_emotion_svg
        return self.emotion_data.get('icon_svg') or get_emotion_svg(self.emotion)

    @property
    def emotion_icon_svg(self):
        from common.icons import get_emotion_svg
        return get_emotion_svg(self.emotion)

    @property
    def emotion_color(self):
        return self.emotion_data.get('color', '#94a3b8')

    @property
    def emotion_percent(self):
        if self.emotion_score is not None:
            return int(round(self.emotion_score * 100))
        return None

    @property
    def voice_emotion_data(self):
        """Métadonnées de l'émotion vocale détectée."""
        from ai.services.emotion_service import get_emotion_meta
        return get_emotion_meta(self.voice_emotion or 'neutre')

    @property
    def voice_emotion_label(self):
        return self.voice_emotion_data.get('label', '')

    @property
    def voice_emotion_percent(self):
        if self.voice_emotion_score is not None:
            return int(round(self.voice_emotion_score * 100))
        return None

    @property
    def is_complete(self):
        completed = ['completed', 'failed', 'skipped']
        return (
            self.summary_status in completed
            and self.sentiment_status in completed
        )

