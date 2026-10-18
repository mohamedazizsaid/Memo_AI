"""
MemoAi — AI Serializers
"""

from rest_framework import serializers
from .models import AIAnalysis


class AIAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysis
        fields = [
            'transcription', 'transcription_language', 'transcription_status',
            'summary', 'keywords', 'mood_insight', 'summary_status',
            'sentiment', 'sentiment_score', 'sentiment_status',
            'generated_image_url', 'image_generation_status',
            'is_complete', 'created_at', 'updated_at',
        ]
        read_only_fields = fields
