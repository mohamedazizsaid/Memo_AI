"""
MemoAi — Persons Serializers
"""

from rest_framework import serializers
from .models import Person, FaceDetection


class PersonSerializer(serializers.ModelSerializer):
    memory_count = serializers.SerializerMethodField()
    has_embedding = serializers.ReadOnlyField()

    def get_memory_count(self, person):
        # List and detail querysets annotate this value to avoid one count query per person.
        if hasattr(person, '_memory_count'):
            return person._memory_count
        return person.memory_count

    class Meta:
        model = Person
        fields = [
            'id', 'name', 'avatar_url', 'notes',
            'memory_count', 'has_embedding', 'is_confirmed',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'memory_count', 'has_embedding']


class PersonUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ['name', 'avatar_url', 'notes', 'is_confirmed']


class FaceDetectionSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)

    class Meta:
        model = FaceDetection
        fields = ['id', 'person', 'confidence', 'bounding_box', 'is_corrected', 'created_at']
        read_only_fields = fields


class AssignFaceSerializer(serializers.Serializer):
    """Reassign a face detection to a different person."""
    person_id = serializers.UUIDField(allow_null=True)


class MergePersonsSerializer(serializers.Serializer):
    """Validate the source person identifier before a merge is attempted."""
    source_person_id = serializers.UUIDField()
