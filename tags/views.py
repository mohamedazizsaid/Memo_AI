"""
MemoAi — Tags Views
CRUD operations and entry associations for tags.
"""

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count

from journal.models import JournalEntry
from journal.serializers import JournalEntryListSerializer
from .models import Tag
from .serializers import TagSerializer, TagCreateUpdateSerializer


class TagListCreateView(generics.ListCreateAPIView):
    """
    List user tags annotated with entry count, or create a new tag.
    Query params:
        - ?q=search_term
    """
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TagCreateUpdateSerializer
        return TagSerializer

    def get_queryset(self):
        qs = (
            Tag.objects
            .filter(user=self.request.user)
            .annotate(entry_count=Count('entries'))
            .order_by('name')
        )
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs


class TagDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a tag.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Tag.objects
            .filter(user=self.request.user)
            .annotate(entry_count=Count('entries'))
        )

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return TagCreateUpdateSerializer
        return TagSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'success': True, 'message': 'Tag deleted.'},
            status=status.HTTP_200_OK,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tag_memories(request, pk):
    """Get all journal entries associated with this tag."""
    try:
        tag = Tag.objects.get(pk=pk, user=request.user)
    except Tag.DoesNotExist:
        return Response({'error': 'Tag not found.'}, status=status.HTTP_404_NOT_FOUND)

    entries = (
        JournalEntry.objects
        .filter(user=request.user, tags=tag)
        .prefetch_related('media', 'tags')
        .order_by('-entry_date')
    )

    return Response(JournalEntryListSerializer(entries, many=True).data)
