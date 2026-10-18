"""
MemoAi — Persons Models
People recognized in photos with face embeddings.
"""

import uuid
from django.db import models
from common.models import TimeStampedModel


class Person(TimeStampedModel):
    """
    A person recognized in photos.
    Face embedding is stored locally — never sent to external services.
    """
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='persons',
        db_index=True,
    )
    name = models.CharField(max_length=255, default='Unknown')
    avatar_url = models.URLField(blank=True)

    # 128-dimensional face embedding stored as comma-separated floats
    # In production, this should be encrypted at rest
    face_embedding = models.TextField(blank=True, null=True)

    # Metadata
    notes = models.TextField(blank=True)
    is_confirmed = models.BooleanField(default=False)  # User manually confirmed this identity

    class Meta:
        db_table = 'persons'
        verbose_name = 'Person'
        verbose_name_plural = 'Persons'
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'name']),
        ]

    def __str__(self):
        return f"Person({self.name}, user={self.user_id})"

    @property
    def memory_count(self):
        return self.face_detections.values('media__entry').distinct().count()

    @property
    def has_embedding(self):
        return bool(self.face_embedding)


class FaceDetection(TimeStampedModel):
    """
    A face detected in a media file, linked to a Person.
    """
    media = models.ForeignKey(
        'media_app.Media',
        on_delete=models.CASCADE,
        related_name='face_detections',
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='face_detections',
    )
    confidence = models.FloatField(default=1.0)
    bounding_box = models.JSONField(default=dict)  # {top, right, bottom, left}
    is_corrected = models.BooleanField(default=False)  # User manually corrected

    class Meta:
        db_table = 'face_detections'
        verbose_name = 'Face Detection'
        verbose_name_plural = 'Face Detections'
        indexes = [
            models.Index(fields=['media', 'person']),
        ]

    def __str__(self):
        return f"FaceDetection(person={self.person_id}, media={self.media_id})"
