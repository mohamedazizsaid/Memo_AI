"""
MemoAi — Journal Template Views
HTML interface for journal entries.
"""

import logging
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.core.paginator import Paginator

from .models import JournalEntry

logger = logging.getLogger('memoai')

MOOD_EMOJIS = {
    'amazing': '🤩', 'good': '😊', 'neutral': '😐', 'sad': '😢',
    'stressed': '😤', 'anxious': '😰', 'tired': '😴',
    'angry': '😠', 'excited': '🎉', 'grateful': '🙏',
}


@method_decorator(login_required, name='dispatch')
class HomeView(View):
    """Dashboard / home page."""

    def get(self, request):
        today = timezone.now().date()

        # Today's entry (most recent if multiple created today)
        today_entry = JournalEntry.objects.filter(
            user=request.user, entry_date=today
        ).order_by('-created_at').first()

        # On this day in past years
        on_this_day = JournalEntry.objects.filter(
            user=request.user,
            entry_date__month=today.month,
            entry_date__day=today.day,
        ).exclude(entry_date=today).order_by('-entry_date')[:5]

        # Recent entries
        recent_entries = JournalEntry.objects.filter(
            user=request.user
        ).prefetch_related('media', 'tags').select_related('ai_analysis').order_by('-entry_date')[:6]

        # Stats
        entries_qs = JournalEntry.objects.filter(user=request.user)
        streak = 0
        check = today
        while entries_qs.filter(entry_date=check).exists():
            streak += 1
            check -= timedelta(days=1)

        from django.db.models import Sum
        stats = {
            'total_entries': entries_qs.count(),
            'total_words': entries_qs.aggregate(t=Sum('word_count'))['t'] or 0,
            'streak_days': streak,
            'entries_this_month': entries_qs.filter(entry_date__month=today.month, entry_date__year=today.year).count(),
        }

        return render(request, 'journal/home.html', {
            'today': today,
            'today_entry': today_entry,
            'on_this_day': on_this_day,
            'recent_entries': recent_entries,
            'stats': stats,
        })


@method_decorator(login_required, name='dispatch')
class EntryListView(View):
    """Paginated list with search and filters."""

    def get(self, request):
        qs = JournalEntry.objects.filter(
            user=request.user
        ).prefetch_related('media', 'tags').select_related('ai_analysis').order_by('-entry_date')

        # Filters
        search = request.GET.get('search', '').strip()
        mood = request.GET.get('mood', '').strip()
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()

        if search:
            from django.db.models import Q
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search) | Q(location__icontains=search))
        if mood:
            qs = qs.filter(mood=mood)
        if date_from:
            qs = qs.filter(entry_date__gte=date_from)
        if date_to:
            qs = qs.filter(entry_date__lte=date_to)

        paginator = Paginator(qs, 12)
        page = paginator.get_page(request.GET.get('page', 1))

        return render(request, 'journal/list.html', {
            'entries': page,
            'page_obj': page,
            'is_paginated': paginator.num_pages > 1,
        })


@method_decorator(login_required, name='dispatch')
class EntryDetailView(View):
    def get(self, request, pk):
        entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
        return render(request, 'journal/detail.html', {'entry': entry})


@method_decorator(login_required, name='dispatch')
class EntryCreateView(View):
    def get(self, request):
        from tags.models import Tag
        user_tags = Tag.objects.filter(user=request.user)
        return render(request, 'journal/form.html', {
            'entry': None,
            'form': {},
            'today': timezone.now().date().isoformat(),
            'mood_choices': JournalEntry.MOOD_CHOICES,
            'mood_emojis': MOOD_EMOJIS,
            'user_tags': user_tags,
        })

    def post(self, request):
        from tags.models import Tag
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        mood = request.POST.get('mood', '').strip()
        location = request.POST.get('location', '').strip()
        entry_date_str = request.POST.get('entry_date', '').strip()
        tag_ids = request.POST.getlist('tags')

        if not entry_date_str:
            entry_date_str = timezone.now().date().isoformat()

        entry = JournalEntry.objects.create(
            user=request.user,
            title=title,
            content=content,
            mood=mood,
            location=location,
            entry_date=entry_date_str,
        )

        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids, user=request.user)
            entry.tags.set(tags)

        # Trigger AI
        if content:
            try:
                from ai.tasks import analyze_entry
                task = analyze_entry.delay(str(entry.id))
                entry.ai_task_id = task.id
                entry.ai_status = 'processing'
                entry.save(update_fields=['ai_task_id', 'ai_status'])
            except Exception as e:
                logger.warning(f'AI trigger failed: {e}')

        messages.success(request, 'Entree creee avec succes !')
        return redirect('journal:detail', pk=entry.pk)


@method_decorator(login_required, name='dispatch')
class EntryEditView(View):
    def get(self, request, pk):
        entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
        from tags.models import Tag
        user_tags = Tag.objects.filter(user=request.user)
        return render(request, 'journal/form.html', {
            'entry': entry,
            'form': {
                'title': {'value': entry.title},
                'content': {'value': entry.content},
                'mood': {'value': entry.mood},
                'location': {'value': entry.location},
                'entry_date': {'value': entry.entry_date.isoformat()},
            },
            'today': timezone.now().date().isoformat(),
            'mood_choices': JournalEntry.MOOD_CHOICES,
            'mood_emojis': MOOD_EMOJIS,
            'user_tags': user_tags,
        })

    def post(self, request, pk):
        entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
        from tags.models import Tag

        entry.title = request.POST.get('title', entry.title).strip()
        entry.content = request.POST.get('content', entry.content).strip()
        entry.mood = request.POST.get('mood', entry.mood).strip()
        entry.location = request.POST.get('location', entry.location).strip()
        entry_date_str = request.POST.get('entry_date', '').strip()
        if entry_date_str:
            entry.entry_date = entry_date_str

        tag_ids = request.POST.getlist('tags')
        entry.save()

        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids, user=request.user)
            entry.tags.set(tags)
        else:
            entry.tags.clear()

        if entry.content:
            try:
                from ai.tasks import analyze_entry
                task = analyze_entry.delay(str(entry.id))
                entry.ai_task_id = task.id
                entry.ai_status = 'processing'
                entry.save(update_fields=['ai_task_id', 'ai_status'])
            except Exception as e:
                logger.warning(f'AI trigger failed: {e}')

        messages.success(request, 'Entree modifiee.')
        return redirect('journal:detail', pk=entry.pk)


@login_required
def entry_delete(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Entree supprimee.')
        return redirect('journal:list')
    return redirect('journal:detail', pk=pk)


@login_required
def trigger_ai_template(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        try:
            from ai.tasks import analyze_entry
            task = analyze_entry.delay(str(entry.id))
            entry.ai_task_id = task.id
            entry.ai_status = 'processing'
            entry.save(update_fields=['ai_task_id', 'ai_status'])
            messages.success(request, 'Analyse IA lancee.')
        except Exception as e:
            logger.warning(f'AI trigger failed: {e}')
            messages.error(request, 'Erreur lors du lancement de l''analyse.')
    return redirect('journal:detail', pk=pk)
