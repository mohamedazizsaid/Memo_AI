"""
MemoAi — AI Insights Views
Analytics and personalized insights for the AI Insights dashboard.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger('memoai')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sentiment_timeline(request):
    """
    Sentiment evolution over time.
    Returns daily average sentiment scores for the last N days.
    """
    days = int(request.query_params.get('days', 30))
    user = request.user
    start_date = timezone.now().date() - timedelta(days=days)

    from journal.models import JournalEntry
    from ai.models import AIAnalysis

    entries = (
        JournalEntry.objects
        .filter(user=user, entry_date__gte=start_date)
        .prefetch_related('ai_analysis')
        .order_by('entry_date')
    )

    timeline = []
    for entry in entries:
        try:
            analysis = entry.ai_analysis
            if analysis.sentiment and analysis.sentiment_score is not None:
                timeline.append({
                    'date': entry.entry_date.isoformat(),
                    'sentiment': analysis.sentiment,
                    'score': analysis.sentiment_score,
                    'entry_id': str(entry.id),
                    'title': entry.title or entry.excerpt[:50],
                })
        except AIAnalysis.DoesNotExist:
            pass

    return Response(timeline)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_keywords(request):
    """Most frequent keywords across all entries."""
    from ai.models import AIAnalysis
    from journal.models import JournalEntry

    limit = int(request.query_params.get('limit', 20))
    days = int(request.query_params.get('days', 90))
    start_date = timezone.now().date() - timedelta(days=days)

    analyses = AIAnalysis.objects.filter(
        entry__user=request.user,
        entry__entry_date__gte=start_date,
    ).exclude(keywords=[])

    # Aggregate keywords
    keyword_count = {}
    for analysis in analyses:
        for kw in analysis.keywords:
            kw_lower = kw.lower().strip()
            if kw_lower:
                keyword_count[kw_lower] = keyword_count.get(kw_lower, 0) + 1

    # Sort by count
    sorted_keywords = sorted(keyword_count.items(), key=lambda x: x[1], reverse=True)[:limit]

    return Response([{'keyword': kw, 'count': count} for kw, count in sorted_keywords])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mood_distribution(request):
    """Distribution of moods across all entries."""
    from journal.models import JournalEntry

    days = int(request.query_params.get('days', 90))
    start_date = timezone.now().date() - timedelta(days=days)

    mood_data = (
        JournalEntry.objects
        .filter(user=request.user, entry_date__gte=start_date)
        .exclude(mood='')
        .values('mood')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    return Response([{'mood': m['mood'], 'count': m['count']} for m in mood_data])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_locations(request):
    """Most frequent locations."""
    from journal.models import JournalEntry

    locations = (
        JournalEntry.objects
        .filter(user=request.user)
        .exclude(location='')
        .values('location')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    return Response([{'location': l['location'], 'count': l['count']} for l in locations])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def writing_activity(request):
    """Writing activity heatmap data (entries per day)."""
    from journal.models import JournalEntry

    days = int(request.query_params.get('days', 365))
    start_date = timezone.now().date() - timedelta(days=days)

    entries = (
        JournalEntry.objects
        .filter(user=request.user, entry_date__gte=start_date)
        .values('entry_date')
        .annotate(count=Count('id'), total_words=Count('word_count'))
        .order_by('entry_date')
    )

    return Response([{
        'date': e['entry_date'].isoformat(),
        'count': e['count'],
    } for e in entries])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weekly_summary_insight(request):
    """Generate a narrative weekly summary via Gemini."""
    from journal.models import JournalEntry
    from ai.models import AIAnalysis

    week_start = timezone.now().date() - timedelta(days=7)

    entries = JournalEntry.objects.filter(
        user=request.user,
        entry_date__gte=week_start,
    ).prefetch_related('ai_analysis')

    # Gather week data
    keywords = []
    moods = []
    locations = []

    for entry in entries:
        if entry.mood:
            moods.append(entry.mood)
        if entry.location:
            locations.append(entry.location)
        try:
            keywords.extend(entry.ai_analysis.keywords or [])
        except AIAnalysis.DoesNotExist:
            pass

    from collections import Counter
    top_keywords = [kw for kw, _ in Counter(keywords).most_common(5)]
    dominant_mood = Counter(moods).most_common(1)[0][0] if moods else None

    week_data = {
        'total_entries': entries.count(),
        'dominant_mood': dominant_mood,
        'top_keywords': top_keywords,
        'locations': list(set(locations))[:5],
    }

    # Get user language preference
    try:
        lang = request.user.preferences.language
    except Exception:
        lang = 'fr'

    from ai.services.gemini_service import generate_weekly_summary
    summary = generate_weekly_summary(week_data, language=lang)

    return Response({
        'summary': summary,
        'data': week_data,
        'week_start': week_start.isoformat(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_people(request):
    """People most present in memories."""
    from persons.models import Person, FaceDetection

    people = (
        Person.objects
        .filter(user=request.user)
        .annotate(
            appearance_count=Count('face_detections', distinct=True)
        )
        .order_by('-appearance_count')[:10]
    )

    from persons.serializers import PersonSerializer
    return Response(PersonSerializer(people, many=True).data)
