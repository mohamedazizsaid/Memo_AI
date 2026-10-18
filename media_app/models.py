"""
MemoAi — Media Models
Photos, audio files, and generated images linked to journal entries.
"""

import uuid
from django.db import models
from common.models import TimeStampedModel


class Media(TimeStampedModel):
    """
    Media file linked to a journal entry.
    Stored in Cloudinary, referenced by URL.
    """
    MEDIA_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('AUDIO', 'Audio'),
        ('GENERATED_IMAGE', 'Generated Image'),
    ]

    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    entry = models.ForeignKey(
        'journal.JournalEntry',
        on_delete=models.CASCADE,
        related_name='media',
        db_index=True,
    )
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, db_index=True)
    storage_url = models.URLField(max_length=1000)
    cloudinary_public_id = models.CharField(max_length=500, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveIntegerField(default=0)  # bytes
    duration_seconds = models.FloatField(null=True, blank=True)  # for audio
    width = models.PositiveIntegerField(null=True, blank=True)  # for images
    height = models.PositiveIntegerField(null=True, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)

    # Processing status for face detection / transcription
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='pending'
    )
    processing_task_id = models.CharField(max_length=255, blank=True)
    processing_error = models.TextField(blank=True)

    class Meta:
        db_table = 'media_files'
        verbose_name = 'Media'
        verbose_name_plural = 'Media Files'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['entry', 'media_type']),
            models.Index(fields=['processing_status']),
        ]

    def __str__(self):
        return f"Media({self.media_type}, {self.entry_id})"

    @property
    def thumbnail_url(self):
        """Generate Cloudinary thumbnail URL for images."""
        if self.media_type == 'IMAGE' and self.cloudinary_public_id:
            return f"https://res.cloudinary.com/{self.cloudinary_public_id}?w=400&h=300&c=fill"
        return self.storage_url

    @property
    def file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2)
