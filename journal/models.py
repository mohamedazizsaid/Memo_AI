"""
MemoAi — Journal Models
Core journal entries with rich metadata.
"""

import uuid
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from common.models import SoftDeleteModel


class JournalEntry(SoftDeleteModel):
    """
    Central model representing a journal entry.
    """
    MOOD_CHOICES = [
        ('amazing', 'Amazing'),
        ('good', 'Good'),
        ('neutral', 'Neutral'),
        ('sad', 'Sad'),
        ('stressed', 'Stressed'),
        ('anxious', 'Anxious'),
        ('tired', 'Tired'),
        ('angry', 'Angry'),
        ('excited', 'Excited'),
        ('grateful', 'Grateful'),
    ]

    MOOD_EMOJI = {
        'amazing': '🤩',
        'good': '😊',
        'neutral': '😐',
        'sad': '😢',
        'stressed': '😤',
        'anxious': '😰',
        'tired': '😴',
        'angry': '😠',
        'excited': '🎉',
        'grateful': '🙏',
    }

    AI_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='journal_entries',
        db_index=True,
    )
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    entry_date = models.DateField(db_index=True)

    # Location
    location = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Mood
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, blank=True)

    # Tags (M2M through EntryTag)
    tags = models.ManyToManyField(
        'tags.Tag',
        through='tags.EntryTag',
        blank=True,
        related_name='entries',
    )

    # AI processing status
    ai_status = models.CharField(max_length=20, choices=AI_STATUS_CHOICES, default='pending')
    ai_task_id = models.CharField(max_length=255, blank=True)
    ai_error_message = models.TextField(blank=True)

    # Word count (updated on save)
    word_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'journal_entries'
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'
        ordering = ['-entry_date', '-created_at']
        indexes = [
            models.Index(fields=['user', '-entry_date']),
            models.Index(fields=['user', 'mood']),
            models.Index(fields=['user', 'ai_status']),
            models.Index(fields=['deleted_at']),
        ]

    def __str__(self):
        return f"Entry({self.user.email}, {self.entry_date}, {self.title or 'Untitled'})"

    def save(self, *args, **kwargs):
        # Update word count on save
        if self.content:
            self.word_count = len(self.content.split())
        super().save(*args, **kwargs)

    @property
    def mood_emoji(self):
        return self.MOOD_EMOJI.get(self.mood, '')

    @property
    def has_audio(self):
        return self.media.filter(media_type='AUDIO').exists()

    @property
    def has_images(self):
        return self.media.filter(media_type='IMAGE').exists()

    @property
    def cover_image_url(self):
        """Best image to illustrate the entry: first photo, else AI illustration."""
        first = self.media.filter(media_type='IMAGE').exclude(storage_url='').first()
        if first:
            return first.storage_url
        try:
            analysis = self.ai_analysis
            if analysis and analysis.generated_image_url:
                return analysis.generated_image_url
        except Exception:
            pass
        return ''

    @property
    def excerpt(self):
        if not self.content:
            return ''
        # Drop the editor's markdown markers so cards show clean prose.
        text = self.content.replace('**', '').replace('*', '')
        return text[:200] + ('...' if len(text) > 200 else '')

    @property
    def detected_emotion(self):
        try:
            if hasattr(self, 'ai_analysis') and self.ai_analysis.emotion:
                return self.ai_analysis.emotion
        except Exception:
            pass
        return ''

    @property
    def detected_emotion_data(self):
        try:
            if hasattr(self, 'ai_analysis') and self.ai_analysis.emotion:
                return self.ai_analysis.emotion_data
        except Exception:
            pass
        return {}

    @property
    def detected_emotion_percent(self):
        try:
            if hasattr(self, 'ai_analysis') and self.ai_analysis.emotion_percent is not None:
                return self.ai_analysis.emotion_percent
        except Exception:
            pass
        return None

