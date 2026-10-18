"""
MemoAi — Notifications Models
In-app and system notifications for daily reminders, AI progress, and nostalgia milestones.
"""

import uuid
from django.db import models


class Notification(models.Model):
    """
    User notifications for journal milestones, AI processing, and reminders.
    """
    TYPE_CHOICES = [
        ('ai_complete', 'AI Processing Complete'),
        ('memory_nostalgia', 'On This Day Memory'),
        ('daily_reminder', 'Daily Journal Reminder'),
        ('weekly_summary', 'Weekly Summary Ready'),
        ('monthly_review', 'Monthly Review Ready'),
        ('streak_milestone', 'Streak Milestone'),
        ('system', 'System Notice'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        default='system',
        db_index=True,
    )
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"Notification({self.user.email}: {self.title})"
