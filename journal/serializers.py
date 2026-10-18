"""
MemoAi — Journal Serializers
Entry creation, update, list, and detailed views.
"""

from rest_framework import serializers
from .models import JournalEntry
from media_app.serializers import MediaSerializer
from ai.serializers import AIAnalysisSerializer
from tags.serializers import TagSerializer


class JournalEntryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    mood_emoji = serializers.ReadOnlyField()
    excerpt = serializers.ReadOnlyField()
    has_audio = serializers.ReadOnlyField()
    has_images = serializers.ReadOnlyField()
    tags = TagSerializer(many=True, read_only=True)
    media_count = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'title', 'excerpt', 'entry_date', 'mood', 'mood_emoji',
            'location', 'tags', 'ai_status', 'has_audio', 'has_images',
            'word_count', 'media_count', 'thumbnail', 'created_at', 'updated_at',
        ]

    def get_media_count(self, obj):
        return obj.media.count()

    def get_thumbnail(self, obj):
        first_image = obj.media.filter(media_type='IMAGE').first()
        if first_image:
            return first_image.storage_url
        return None


class JournalEntryDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail views."""
    mood_emoji = serializers.ReadOnlyField()
    excerpt = serializers.ReadOnlyField()
    has_audio = serializers.ReadOnlyField()
    has_images = serializers.ReadOnlyField()
    tags = TagSerializer(many=True, read_only=True)
    media = MediaSerializer(many=True, read_only=True)
    ai_analysis = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'title', 'content', 'excerpt', 'entry_date', 'mood', 'mood_emoji',
            'location', 'latitude', 'longitude',
            'tags', 'media', 'ai_analysis', 'ai_status', 'ai_error_message',
            'has_audio', 'has_images', 'word_count', 'created_at', 'updated_at',
        ]


    def get_ai_analysis(self, obj):
        try:
            return AIAnalysisSerializer(obj.ai_analysis).data
        except Exception:
            return None


class JournalEntryCreateSerializer(serializers.ModelSerializer):
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        allow_empty=True,
    )

    class Meta:
        model = JournalEntry
        fields = [
            'title', 'content', 'entry_date', 'mood',
            'location', 'latitude', 'longitude', 'tag_ids',
        ]

    def validate_entry_date(self, value):
        from django.utils import timezone
        import datetime
        today = timezone.now().date()
        # Allow entries from the past but not more than 100 years ago
        if value < today - datetime.timedelta(days=365 * 100):
            raise serializers.ValidationError("Entry date is too far in the past.")
        # Allow entries up to 1 day in the future
        if value > today + datetime.timedelta(days=1):
            raise serializers.ValidationError("Entry date cannot be in the future.")
        return value

    def create(self, validated_data):
        from tags.models import Tag
        tag_ids = validated_data.pop('tag_ids', [])
        user = self.context['request'].user
        entry = JournalEntry.objects.create(user=user, **validated_data)

        # Associate tags (only user's own tags)
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids, user=user)
            entry.tags.set(tags)

        return entry


class JournalEntryUpdateSerializer(serializers.ModelSerializer):
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        allow_empty=True,
    )

    class Meta:
        model = JournalEntry
        fields = [
            'title', 'content', 'entry_date', 'mood',
            'location', 'latitude', 'longitude', 'tag_ids',
        ]

    def update(self, instance, validated_data):
        from tags.models import Tag
        tag_ids = validated_data.pop('tag_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tag_ids is not None:
            user = self.context['request'].user
            tags = Tag.objects.filter(id__in=tag_ids, user=user)
            instance.tags.set(tags)

        return instance


class JournalStatsSerializer(serializers.Serializer):
    """Statistics summary for a user's journal."""
    total_entries = serializers.IntegerField()
    total_words = serializers.IntegerField()
    streak_days = serializers.IntegerField()
    entries_this_week = serializers.IntegerField()
    entries_this_month = serializers.IntegerField()
    most_used_mood = serializers.CharField(allow_null=True)
    most_used_tags = TagSerializer(many=True)
    entries_by_mood = serializers.DictField()
