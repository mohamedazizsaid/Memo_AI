"""
MemoAi — Persons Views
People management: list, rename, merge, delete, correct face associations.
"""

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count

from common.permissions import IsOwner
from journal.models import JournalEntry
from journal.serializers import JournalEntryListSerializer
from .models import Person, FaceDetection
from .serializers import PersonSerializer, PersonUpdateSerializer, AssignFaceSerializer


class PersonListView(generics.ListAPIView):
    """List all recognized persons for the current user."""
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Person.objects.filter(user=self.request.user).annotate(
            _memory_count=Count('face_detections__media__entry', distinct=True),
        )


class PersonDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a specific person."""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Person.objects.filter(user=self.request.user).annotate(
            _memory_count=Count('face_detections__media__entry', distinct=True),
        )

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PersonUpdateSerializer
        return PersonSerializer

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        person = self.get_object()
        # Clear face detections pointing to this person (don't delete media)
        FaceDetection.objects.filter(person=person).update(person=None)
        person.delete()
        return Response({'success': True, 'message': 'Person deleted.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def person_memories(request, pk):
    """Get all journal entries where this person appears."""
    try:
        person = Person.objects.get(pk=pk, user=request.user)
    except Person.DoesNotExist:
        return Response({'error': 'Person not found.'}, status=status.HTTP_404_NOT_FOUND)

    entries = (
        JournalEntry.objects
        .filter(
            user=request.user,
            media__face_detections__person=person,
        )
        .distinct()
        .prefetch_related('media', 'tags')
        .order_by('-entry_date')
    )

    return Response(JournalEntryListSerializer(entries, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def merge_persons(request, pk):
    """
    Merge two persons into one (pk is the target person to keep).
    Expects: {'source_person_id': uuid}
    """
    try:
        target = Person.objects.get(pk=pk, user=request.user)
    except Person.DoesNotExist:
        return Response({'error': 'Target person not found.'}, status=status.HTTP_404_NOT_FOUND)

    source_id = request.data.get('source_person_id')
    if not source_id:
        return Response({'error': 'source_person_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        source = Person.objects.get(pk=source_id, user=request.user)
    except Person.DoesNotExist:
        return Response({'error': 'Source person not found.'}, status=status.HTTP_404_NOT_FOUND)

    if str(target.id) == str(source.id):
        return Response({'error': 'Cannot merge person with themselves.'}, status=status.HTTP_400_BAD_REQUEST)

    # Move all face detections from source to target
    FaceDetection.objects.filter(person=source).update(person=target)
    source.delete()

    return Response({'success': True, 'person': PersonSerializer(target).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_face(request, detection_id):
    """
    Reassign a face detection to a different person (or create new).
    Corrects auto-detection errors.
    """
    serializer = AssignFaceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        detection = FaceDetection.objects.select_related('media__entry').get(pk=detection_id)
        # Verify user owns the media
        if detection.media.entry.user != request.user:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    except FaceDetection.DoesNotExist:
        return Response({'error': 'Detection not found.'}, status=status.HTTP_404_NOT_FOUND)

    person_id = serializer.validated_data.get('person_id')
    if person_id:
        try:
            person = Person.objects.get(pk=person_id, user=request.user)
            detection.person = person
        except Person.DoesNotExist:
            return Response({'error': 'Person not found.'}, status=status.HTTP_404_NOT_FOUND)
    else:
        detection.person = None

    detection.is_corrected = True
    detection.save()

    return Response({'success': True})
