"""
MemoAi — AI Template Views
HTML interface for AI insights.
"""

import logging
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from journal.models import JournalEntry

logger = logging.getLogger('memoai')


@method_decorator(login_required, name='dispatch')
class InsightsView(View):
    def get(self, request):
        period = request.GET.get('period', '30')
        try:
            days = int(period)
        except ValueError:
            days = 30

        today = timezone.now().date()
        since = today - timedelta(days=days)

        entries = JournalEntry.objects.filter(user=request.user, entry_date__gte=since)
        all_entries = JournalEntry.objects.filter(user=request.user)

        from django.db.models import Count, Sum

        # Streak
        streak = 0
        check = today
        while all_entries.filter(entry_date=check).exists():
            streak += 1
            check -= timedelta(days=1)

        # Mood distribution
        mood_qs = entries.exclude(mood='').values('mood').annotate(count=Count('id')).order_by('-count')
        entries_by_mood = {m['mood']: m['count'] for m in mood_qs}
        most_used_mood = mood_qs[0]['mood'] if mood_qs else None

        # Top tags
        from tags.models import Tag
        top_tags = (
            Tag.objects.filter(user=request.user, entries__isnull=False)
            .annotate(entry_count=Count('entries'))
            .order_by('-entry_count')[:5]
        )

        week_start = today - timedelta(days=7)
        month_start = today.replace(day=1)

        stats = {
            'total_entries': all_entries.count(),
            'total_words': all_entries.aggregate(t=Sum('word_count'))['t'] or 0,
            'streak_days': streak,
            'most_used_mood': most_used_mood,
            'entries_by_mood': entries_by_mood,
            'most_used_tags': top_tags,
            'entries_this_week': all_entries.filter(entry_date__gte=week_start).count(),
            'entries_this_month': all_entries.filter(entry_date__gte=month_start).count(),
        }

        # AI insights
        insights = []
        try:
            from ai.models import AIAnalysis
            insights = AIAnalysis.objects.filter(
                entry__user=request.user,
                summary__gt=''
            ).select_related('entry').order_by('-created_at')[:10]
        except Exception:
            pass

        return render(request, 'ai/insights.html', {
            'stats': stats,
            'insights': insights,
            'period': period,
        })
