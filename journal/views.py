"""
MemoAi — Journal Views
Journal entry CRUD with search, filtering, and AI integration.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Q
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from common.permissions import IsOwner
from .models import JournalEntry
from .serializers import (
    JournalEntryListSerializer,
    JournalEntryDetailSerializer,
    JournalEntryCreateSerializer,
    JournalEntryUpdateSerializer,
)

logger = logging.getLogger('memoai')


class JournalEntryFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='entry_date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='entry_date', lookup_expr='lte')
    mood = django_filters.MultipleChoiceFilter(choices=JournalEntry.MOOD_CHOICES)
    has_audio = django_filters.BooleanFilter(method='filter_has_audio')
    has_images = django_filters.BooleanFilter(method='filter_has_images')
    tags = django_filters.CharFilter(method='filter_tags')
    person = django_filters.UUIDFilter(method='filter_person')

    class Meta:
        model = JournalEntry
        fields = ['mood', 'date_from', 'date_to']

    def filter_has_audio(self, queryset, name, value):
        if value:
            return queryset.filter(media__media_type='AUDIO').distinct()
        return queryset.exclude(media__media_type='AUDIO').distinct()

    def filter_has_images(self, queryset, name, value):
        if value:
            return queryset.filter(media__media_type='IMAGE').distinct()
        return queryset.exclude(media__media_type='IMAGE').distinct()

    def filter_tags(self, queryset, name, value):
        tag_ids = [t.strip() for t in value.split(',') if t.strip()]
        if tag_ids:
            return queryset.filter(tags__id__in=tag_ids).distinct()
        return queryset

    def filter_person(self, queryset, name, value):
        return queryset.filter(
            media__face_detections__person_id=value
        ).distinct()


class JournalEntryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/entries/  - List user's entries with search & filters
    POST /api/entries/  - Create new entry
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = JournalEntryFilter
    search_fields = ['title', 'content', 'location']
    ordering_fields = ['entry_date', 'created_at', 'word_count']
    ordering = ['-entry_date']

    def get_queryset(self):
        return (
            JournalEntry.objects
            .filter(user=self.request.user)
            .prefetch_related('media', 'tags')
            .select_related('user')
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return JournalEntryCreateSerializer
        return JournalEntryListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        entry = serializer.save()

        # Trigger AI pipeline if content or audio present
        if entry.content:
            from ai.tasks import analyze_entry
            task = analyze_entry.delay(str(entry.id))
            entry.ai_task_id = task.id
            entry.ai_status = 'processing'
            entry.save(update_fields=['ai_task_id', 'ai_status'])

        return Response(
            JournalEntryDetailSerializer(entry).data,
            status=status.HTTP_201_CREATED
        )


class JournalEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/entries/{id}/  - Entry detail
    PATCH  /api/entries/{id}/  - Update entry
    DELETE /api/entries/{id}/  - Soft delete entry
    """
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        return (
            JournalEntry.objects
            .filter(user=self.request.user)
            .prefetch_related('media', 'tags', 'ai_analysis')
            .select_related('user')
        )

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return JournalEntryUpdateSerializer
        return JournalEntryDetailSerializer

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        entry = serializer.save()

        # Re-trigger AI if content changed
        if 'content' in request.data and entry.content:
            from ai.tasks import analyze_entry
            task = analyze_entry.delay(str(entry.id))
            entry.ai_task_id = task.id
            entry.ai_status = 'processing'
            entry.save(update_fields=['ai_task_id', 'ai_status'])

        return Response(JournalEntryDetailSerializer(entry).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()  # Soft delete
        return Response(
            {'success': True, 'message': 'Entry deleted.'},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def journal_stats(request):
    """Journal statistics for the dashboard."""
    user = request.user
    today = timezone.now().date()
    week_start = today - timedelta(days=7)
    month_start = today.replace(day=1)

    entries = JournalEntry.objects.filter(user=user)

    # Streak calculation
    streak = 0
    check_date = today
    while entries.filter(entry_date=check_date).exists():
        streak += 1
        check_date -= timedelta(days=1)

    # Mood distribution
    mood_counts = (
        entries.exclude(mood='')
        .values('mood')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    entries_by_mood = {m['mood']: m['count'] for m in mood_counts}
    most_used_mood = mood_counts[0]['mood'] if mood_counts else None

    # Top tags
    from tags.models import Tag
    top_tags = (
        Tag.objects.filter(user=user, entries__isnull=False)
        .annotate(entry_count=Count('entries'))
        .order_by('-entry_count')[:5]
    )

    from tags.serializers import TagSerializer
    return Response({
        'total_entries': entries.count(),
        'total_words': entries.aggregate(total=Sum('word_count'))['total'] or 0,
        'streak_days': streak,
        'entries_this_week': entries.filter(entry_date__gte=week_start).count(),
        'entries_this_month': entries.filter(entry_date__gte=month_start).count(),
        'most_used_mood': most_used_mood,
        'most_used_tags': TagSerializer(top_tags, many=True).data,
        'entries_by_mood': entries_by_mood,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_ai_analysis(request, pk):
    """Manually trigger AI analysis for an entry."""
    try:
        entry = JournalEntry.objects.get(pk=pk, user=request.user)
    except JournalEntry.DoesNotExist:
        return Response({'error': 'Entry not found.'}, status=status.HTTP_404_NOT_FOUND)

    from ai.tasks import analyze_entry
    task = analyze_entry.delay(str(entry.id))
    entry.ai_task_id = task.id
    entry.ai_status = 'processing'
    entry.save(update_fields=['ai_task_id', 'ai_status'])

    return Response({'success': True, 'task_id': task.id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def today_entry(request):
    """Get today's entry if it exists."""
    today = timezone.now().date()
    entry = JournalEntry.objects.filter(
        user=request.user, entry_date=today
    ).order_by('-created_at').first()
    if entry:
        return Response(JournalEntryDetailSerializer(entry).data)
    return Response(None, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def on_this_day(request):
    """Get entries from the same day in previous years."""
    today = timezone.now().date()
    entries = JournalEntry.objects.filter(
        user=request.user,
        entry_date__month=today.month,
        entry_date__day=today.day,
    ).exclude(entry_date=today).order_by('-entry_date')[:10]

    return Response(JournalEntryListSerializer(entries, many=True).data)
