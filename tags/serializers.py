"""
MemoAi — Tags Serializers
"""

from rest_framework import serializers
from .models import Tag, EntryTag


class TagSerializer(serializers.ModelSerializer):
    entry_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'color', 'icon',
            'is_ai_suggested', 'entry_count', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class TagCreateUpdateSerializer(serializers.ModelSerializer):
    entry_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'icon', 'is_ai_suggested', 'entry_count', 'created_at']
        read_only_fields = ['id', 'is_ai_suggested', 'entry_count', 'created_at']


    def validate_name(self, value):
        user = self.context['request'].user
        # Check uniqueness per user on create or rename
        instance = self.instance
        qs = Tag.objects.filter(user=user, name__iexact=value.strip())
        if instance:
            qs = qs.exclude(id=instance.id)
        if qs.exists():
            raise serializers.ValidationError("You already have a tag with this name.")
        return value.strip()

    def create(self, validated_data):
        user = self.context['request'].user
        return Tag.objects.create(user=user, **validated_data)
