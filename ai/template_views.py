"""
MemoAi — AI Template Views
HTML interface for AI insights. Everything here is derived from the user's own
journal data — there are no hard-coded figures.
"""

import logging
from collections import Counter
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from common.cloud_media import image_variant
from journal.models import JournalEntry

logger = logging.getLogger('memoai')

PERIOD_LABELS = {'7': '7', '30': '30', '90': '90', '365': '365'}

# Mood keys are stored in English in the database; the dashboard shows a
# readable, localized label with a hue used by the mood bars.
MOOD_META = {
    'amazing': {'fr': 'Incroyable', 'en': 'Amazing', 'emoji': '🤩', 'hue': '#c8963e'},
    'good': {'fr': 'Bien', 'en': 'Good', 'emoji': '😊', 'hue': '#b08a4f'},
    'neutral': {'fr': 'Neutre', 'en': 'Neutral', 'emoji': '😐', 'hue': '#a8a29e'},
    'sad': {'fr': 'Triste', 'en': 'Sad', 'emoji': '😢', 'hue': '#8b8580'},
    'stressed': {'fr': 'Stresse', 'en': 'Stressed', 'emoji': '😤', 'hue': '#b4654a'},
    'anxious': {'fr': 'Anxieux', 'en': 'Anxious', 'emoji': '😰', 'hue': '#9c8064'},
    'tired': {'fr': 'Fatigue', 'en': 'Tired', 'emoji': '😴', 'hue': '#706a64'},
    'angry': {'fr': 'En colere', 'en': 'Angry', 'emoji': '😠', 'hue': '#9e4a36'},
    'excited': {'fr': 'Excité', 'en': 'Excited', 'emoji': '🎉', 'hue': '#d6a24c'},
    'grateful': {'fr': 'Reconnaissant', 'en': 'Grateful', 'emoji': '🙏', 'hue': '#a8895f'},
}

SENTIMENT_META = (
    ('positive', {'fr': 'Positif', 'en': 'Positive', 'hue': '#c8963e'}),
    ('neutral', {'fr': 'Neutre', 'en': 'Neutral', 'hue': '#a8a29e'}),
    ('negative', {'fr': 'Negatif', 'en': 'Negative', 'hue': '#a34e39'}),
)


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

        prefs = getattr(user, 'preferences', None)
        lang = 'en' if str(getattr(prefs, 'language', 'fr') or 'fr').lower().startswith('en') else 'fr'

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

        mood_rows = []
        for key, count in sorted(entries_by_mood.items(), key=lambda item: (-item[1], item[0])):
            meta = MOOD_META.get(key, {})
            mood_rows.append({
                'key': key,
                'label': meta.get(lang, key.replace('_', ' ').title()),
                'emoji': meta.get('emoji', ''),
                'hue': meta.get('hue', '#a1a1aa'),
                'count': count,
                'percent': int(round(count / max_mood * 100)) if max_mood else 0,
            })

        most_used_mood_label = ''
        if most_used_mood:
            meta = MOOD_META.get(most_used_mood, {})
            most_used_mood_label = f"{meta.get('emoji', '')} {meta.get(lang, most_used_mood.title())}".strip()

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
            # The template draws the bars in pixels: a percentage height inside
            # an auto-sized flex item collapses, which made the old chart lie.
            a['bar_px'] = max(6, int(round((a['count'] / max_activity) * 128)))
            a['is_empty'] = a['count'] == 0
            a['is_peak'] = bool(a['count']) and a['count'] == max_activity

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

        sentiment_rows = []
        for key, meta in SENTIMENT_META:
            count = sentiment_dist.get(key, 0)
            sentiment_rows.append({
                'key': key,
                'label': meta[lang],
                'hue': meta['hue'],
                'count': count,
                'percent': int(round(count / sentiment_total * 100)),
            })

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
            {
                'word': word,
                'count': count,
                'weight': 1 + min(count, 5),
                'size': 13 + min(count, 5) * 2,  # 15px → 23px, readable
            }
            for word, count in keyword_counter.most_common(20)
        ]

        # ── 7-class Emotion analytics (French-emotion ML model) ─────────────
        from ai.services.emotion_service import EMOTION_META
        emotion_dist = {k: 0 for k in EMOTION_META}
        for row in (
            analysis_qs.filter(entry__entry_date__gte=since)
            .exclude(emotion='').values('emotion').annotate(c=Count('id'))
        ):
            if row['emotion'] in emotion_dist:
                emotion_dist[row['emotion']] = row['c']
        emotion_total = sum(emotion_dist.values()) or 1

        emotion_rows = []
        dominant_emotion_key = None
        dominant_emotion_count = -1

        for key, meta in EMOTION_META.items():
            count = emotion_dist.get(key, 0)
            if count > dominant_emotion_count and count > 0:
                dominant_emotion_count = count
                dominant_emotion_key = key
            percent = int(round(count / emotion_total * 100)) if sum(emotion_dist.values()) else 0
            emotion_rows.append({
                'key': key,
                'label': meta.get(lang, meta['fr']),
                'emoji': meta.get('emoji', '😐'),
                'color': meta.get('color', '#94a3b8'),
                'count': count,
                'percent': percent,
            })
        emotion_rows.sort(key=lambda x: -x['count'])

        dominant_emotion = None
        if dominant_emotion_key:
            d_meta = EMOTION_META[dominant_emotion_key]
            dominant_emotion = {
                'key': dominant_emotion_key,
                'label': d_meta.get(lang, d_meta['fr']),
                'emoji': d_meta.get('emoji', '😐'),
                'color': d_meta.get('color', '#94a3b8'),
                'count': dominant_emotion_count,
                'percent': int(round(dominant_emotion_count / emotion_total * 100)),
            }

        # ── Monthly emotion breakdown (Statistiques mensuelles) ─────────────
        french_months = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        monthly_emotions = []
        # Check last 6 distinct months
        for m_offset in range(6):
            cur_month_date = today.replace(day=1)
            # Subtract months safely
            year = cur_month_date.year
            month = cur_month_date.month - m_offset
            while month <= 0:
                month += 12
                year -= 1

            m_entries = analysis_qs.filter(
                entry__entry_date__year=year,
                entry__entry_date__month=month,
            ).exclude(emotion='')

            m_total = m_entries.count()
            if m_total > 0:
                m_counts = Counter(m_entries.values_list('emotion', flat=True))
                top_emo, top_cnt = m_counts.most_common(1)[0]
                top_meta = EMOTION_META.get(top_emo, EMOTION_META['neutre'])

                m_label = f"{french_months[month - 1]} {year}" if lang == 'fr' else f"{today.replace(year=year, month=month).strftime('%B')} {year}"

                breakdown = []
                for emo_k, emo_meta_item in EMOTION_META.items():
                    cnt = m_counts.get(emo_k, 0)
                    if cnt > 0:
                        breakdown.append({
                            'key': emo_k,
                            'label': emo_meta_item.get(lang, emo_meta_item['fr']),
                            'emoji': emo_meta_item['emoji'],
                            'color': emo_meta_item['color'],
                            'count': cnt,
                            'percent': int(round(cnt / m_total * 100)),
                        })
                breakdown.sort(key=lambda x: -x['count'])

                monthly_emotions.append({
                    'month_label': m_label,
                    'year': year,
                    'month': month,
                    'total': m_total,
                    'top_emotion': top_emo,
                    'top_label': top_meta.get(lang, top_meta['fr']),
                    'top_emoji': top_meta['emoji'],
                    'top_color': top_meta['color'],
                    'top_percent': int(round(top_cnt / m_total * 100)),
                    'breakdown': breakdown,
                })

        # ── People recognised in photos ────────────────────────────────────
        from persons.models import Person
        top_persons = []
        for person in (
            Person.objects.filter(user=user)
            .annotate(detections=Count('face_detections'))
            .filter(detections__gt=0)
            .order_by('-detections', 'name')[:8]
        ):
            name = (person.name or 'Unknown').strip()
            top_persons.append({
                'id': person.id,
                'name': name,
                'initial': (name[:1] or '?').upper(),
                'detections': person.detections,
                'avatar_thumb': image_variant(person.avatar_url, 320),
            })

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
            'most_used_mood_label': most_used_mood_label,
            'entries_by_mood': entries_by_mood,
            'mood_rows': mood_rows,
            'max_mood': max_mood,
            'most_used_tags': top_tags,
            'entries_this_week': all_entries.filter(entry_date__gte=week_start).count(),
            'entries_this_month': all_entries.filter(entry_date__gte=month_start).count(),
            'distinct_days': distinct_days,
            'sentiment_dist': sentiment_dist,
            'sentiment_rows': sentiment_rows,
            'sentiment_total': sentiment_total,
            'avg_sentiment': round(avg_sentiment, 3) if avg_sentiment is not None else None,
            'emotion_dist': emotion_dist,
            'emotion_rows': emotion_rows,
            'emotion_total': sum(emotion_dist.values()),
            'dominant_emotion': dominant_emotion,
            'monthly_emotions': monthly_emotions,
            'activity': activity,
            'max_activity': max_activity,
            'keyword_cloud': keyword_cloud,
            'top_persons': top_persons,
        }

        # ── Recent AI insights (real summaries) ────────────────────────────
        insights_qs = (
            analysis_qs.filter(summary__gt='')
            .select_related('entry').order_by('-entry__entry_date')
        )
        insights_paginator = Paginator(insights_qs, 6)
        insights_page = insights_paginator.get_page(request.GET.get('page', 1))

        return render(request, 'ai/insights.html', {
            'stats': stats,
            'insights': insights_page,
            'page_obj': insights_page,
            'is_paginated': insights_paginator.num_pages > 1,
            'period': period,
            'has_ai_data': insights_paginator.count > 0 or bool(keyword_counter),
        })
