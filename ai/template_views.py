"""
MemoAi — AI Template Views
HTML interface for AI insights. Everything here is derived from the user's own
journal data — there are no hard-coded figures.
"""

import logging
from collections import Counter
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from journal.models import JournalEntry

logger = logging.getLogger('memoai')

PERIOD_LABELS = {'7': '7', '30': '30', '90': '90', '365': '365'}


@method_decorator(login_required, name='dispatch')
class InsightsView(View):
    """Real, dynamic analytics for the AI insights dashboard."""

    def get(self, request):
        period = request.GET.get('period', '30')
        try:
            days = int(period)
        except (TypeError, ValueError):
            days = 30
        period = str(days)

        today = timezone.now().date()
        since = today - timedelta(days=days)
        user = request.user

        all_entries = JournalEntry.objects.filter(user=user)
        entries = all_entries.filter(entry_date__gte=since)

        # ── Streak (consecutive days with an entry, ending today) ──────────
        streak = 0
        check = today
        while all_entries.filter(entry_date=check).exists():
            streak += 1
            check -= timedelta(days=1)

        # ── Mood distribution (period) ─────────────────────────────────────
        mood_qs = (
            entries.exclude(mood='').values('mood')
            .annotate(count=Count('id')).order_by('-count')
        )
        entries_by_mood = {m['mood']: m['count'] for m in mood_qs}
        most_used_mood = mood_qs[0]['mood'] if mood_qs else None
        max_mood = max(entries_by_mood.values()) if entries_by_mood else 1

        # ── Top tags ───────────────────────────────────────────────────────
        from tags.models import Tag
        top_tags = (
            Tag.objects.filter(user=user, entries__isnull=False)
            .annotate(entry_count=Count('entries'))
            .order_by('-entry_count')[:6]
        )

        week_start = today - timedelta(days=7)
        month_start = today.replace(day=1)

        # ── Writing activity — last 12 weeks of entries ────────────────────
        activity = []
        bucket_start = today - timedelta(days=(today.weekday()) + 7 * 11)
        for i in range(12):
            start = bucket_start + timedelta(days=7 * i)
            end = start + timedelta(days=6)
            count = all_entries.filter(entry_date__gte=start, entry_date__lte=end).count()
            activity.append({
                'label': start.strftime('%d/%m'),
                'count': count,
            })
        max_activity = max([a['count'] for a in activity] or [1]) or 1
        for a in activity:
            a['height'] = int(round((a['count'] / max_activity) * 100)) if max_activity else 0

        # ── AI-derived analytics (sentiment + keywords) ────────────────────
        from ai.models import AIAnalysis
        analysis_qs = AIAnalysis.objects.filter(entry__user=user)

        sentiment_dist = {'positive': 0, 'neutral': 0, 'negative': 0}
        for row in (
            analysis_qs.filter(entry__entry_date__gte=since)
            .exclude(sentiment='').values('sentiment').annotate(c=Count('id'))
        ):
            if row['sentiment'] in sentiment_dist:
                sentiment_dist[row['sentiment']] = row['c']
        sentiment_total = sum(sentiment_dist.values()) or 1

        avg_sentiment = (
            analysis_qs.filter(entry__entry_date__gte=since, sentiment_score__isnull=False)
            .aggregate(a=Avg('sentiment_score'))['a']
        )

        keyword_counter = Counter()
        for keywords in analysis_qs.filter(entry__entry_date__gte=since).values_list('keywords', flat=True):
            for kw in (keywords or []):
                kw = str(kw).strip().lower()
                if kw:
                    keyword_counter[kw] += 1
        keyword_cloud = [
            {'word': word, 'count': count, 'weight': 1 + min(count, 5)}
            for word, count in keyword_counter.most_common(20)
        ]

        # ── People recognised in photos ────────────────────────────────────
        from persons.models import Person
        top_persons = (
            Person.objects.filter(user=user)
            .annotate(detections=Count('face_detections'))
            .filter(detections__gt=0)
            .order_by('-detections')[:6]
        )

        # ── Distinct days / average length ─────────────────────────────────
        distinct_days = entries.values('entry_date').distinct().count()
        avg_words = all_entries.aggregate(a=Avg('word_count'))['a'] or 0

        stats = {
            'total_entries': all_entries.count(),
            'period_entries': entries.count(),
            'total_words': all_entries.aggregate(t=Sum('word_count'))['t'] or 0,
            'avg_words': int(avg_words),
            'streak_days': streak,
            'most_used_mood': most_used_mood,
            'entries_by_mood': entries_by_mood,
            'max_mood': max_mood,
            'most_used_tags': top_tags,
            'entries_this_week': all_entries.filter(entry_date__gte=week_start).count(),
            'entries_this_month': all_entries.filter(entry_date__gte=month_start).count(),
            'distinct_days': distinct_days,
            'sentiment_dist': sentiment_dist,
            'sentiment_total': sentiment_total,
            'avg_sentiment': round(avg_sentiment, 3) if avg_sentiment is not None else None,
            'activity': activity,
            'max_activity': max_activity,
            'keyword_cloud': keyword_cloud,
            'top_persons': top_persons,
        }

        # ── Recent AI insights (real summaries) ────────────────────────────
        insights = list(
            analysis_qs.filter(summary__gt='')
            .select_related('entry').order_by('-entry__entry_date')[:12]
        )

        return render(request, 'ai/insights.html', {
            'stats': stats,
            'insights': insights,
            'period': period,
            'has_ai_data': bool(insights) or keyword_counter,
        })
