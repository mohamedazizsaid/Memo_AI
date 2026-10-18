"""
MemoAi — Tags Models
User-defined and AI-suggested tags for journal categorization.
"""

import uuid
from django.db import models
from common.models import TimeStampedModel


class Tag(TimeStampedModel):
    """
    Tag for categorizing journal entries.
    Each user has their own tag namespace.
    """
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='tags',
        db_index=True,
    )
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=20, default='#6366f1')
    icon = models.CharField(max_length=50, blank=True)
    is_ai_suggested = models.BooleanField(default=False)

    class Meta:
        db_table = 'tags'
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        unique_together = [['user', 'name']]
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'name']),
        ]

    def __str__(self):
        return f"Tag({self.name}, {self.user.email})"

    @property
    def entry_count(self):
        if hasattr(self, '_entry_count'):
            return self._entry_count
        return self.entries.count()

    @entry_count.setter
    def entry_count(self, value):
        self._entry_count = value



class EntryTag(models.Model):
    """
    Explicit intermediary table between JournalEntry and Tag.
    Tracks whether the tag was manually added or AI-suggested.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(
        'journal.JournalEntry',
        on_delete=models.CASCADE,
        related_name='entry_tags',
    )
    tag = models.ForeignKey(
        'tags.Tag',
        on_delete=models.CASCADE,
        related_name='entry_tags',
    )
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'entry_tags'
        unique_together = [['entry', 'tag']]
        indexes = [
            models.Index(fields=['entry', 'tag']),
        ]

    def __str__(self):
        return f"{self.entry_id} -> {self.tag.name}"
