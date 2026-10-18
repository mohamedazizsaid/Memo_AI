"""
MemoAi — Media Serializers
"""

from rest_framework import serializers
from .models import Media


class MediaSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.ReadOnlyField()
    file_size_mb = serializers.ReadOnlyField()

    class Meta:
        model = Media
        fields = [
            'id', 'media_type', 'storage_url', 'thumbnail_url',
            'cloudinary_public_id', 'mime_type', 'file_size', 'file_size_mb',
            'duration_seconds', 'width', 'height', 'original_filename',
            'processing_status', 'created_at',
        ]
        read_only_fields = ['id', 'storage_url', 'processing_status', 'created_at']


class MediaUploadSerializer(serializers.Serializer):
    """Used for file upload requests."""
    file = serializers.FileField()
    media_type = serializers.ChoiceField(choices=['IMAGE', 'AUDIO'])
    entry_id = serializers.UUIDField()
