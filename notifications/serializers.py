"""
MemoAi — Notifications Serializers
"""

from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type',
            'data', 'is_read', 'read_at', 'created_at',
        ]
        read_only_fields = ['id', 'title', 'message', 'notification_type', 'data', 'created_at']
