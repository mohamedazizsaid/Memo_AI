"""
MemoAi — Platform-wide search.

Powers two things:

* ``search_api`` — the live JSON suggestions used by the navbar omnibox.
* ``SearchResultsView`` — the full results page reached by pressing Enter.

Search covers journal entries, people and tags. Every query is scoped to the
signed-in user, so nothing leaks between accounts.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

MAX_PER_GROUP = 6
RESULTS_PER_GROUP = 30


def _clean(text, length=110):
    """Collapse whitespace and drop the editor's markdown markers."""
    text = (text or '').replace('\r', ' ').replace('\n', ' ')
    text = text.replace('**', '').replace('*', '')
    text = ' '.join(text.split())
    if len(text) > length:
        return text[:length].rstrip() + '…'
    return text


def search_entries(user, query, limit=MAX_PER_GROUP):
    from journal.models import JournalEntry

    queryset = (
        JournalEntry.objects.filter(user=user)
        .filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(location__icontains=query)
        )
        .order_by('-entry_date')[:limit]
    )

    items = []
    for entry in queryset:
        title = entry.title.strip() or entry.entry_date.strftime('%d %B %Y')
        items.append({
            'type': 'entry',
            'title': title,
            'subtitle': _clean(entry.excerpt, 96),
            'badge': entry.entry_date.strftime('%d/%m/%Y'),
            'image': entry.cover_image_url or '',
            'url': reverse('journal:detail', args=[entry.pk]),
        })
    return items


def search_persons(user, query, limit=MAX_PER_GROUP):
    from persons.models import Person

    queryset = (
        Person.objects.filter(user=user)
        .filter(Q(name__icontains=query) | Q(notes__icontains=query))
        .order_by('name')[:limit]
    )

    items = []
    for person in queryset:
        try:
            memories = person.memory_count
        except Exception:  # pragma: no cover - defensive
            memories = 0
        items.append({
            'type': 'person',
            'title': person.name,
            'subtitle': _clean(person.notes, 96),
            'badge': f"{memories} souvenir{'s' if memories != 1 else ''}" if memories else '',
            'image': person.avatar_url or '',
            'url': reverse('persons:detail', args=[person.pk]),
        })
    return items


def search_tags(user, query, limit=MAX_PER_GROUP):
    from tags.models import Tag

    queryset = Tag.objects.filter(user=user, name__icontains=query).order_by('name')[:limit]

    items = []
    for tag in queryset:
        try:
            count = tag.entry_count
        except Exception:  # pragma: no cover - defensive
            count = 0
        items.append({
            'type': 'tag',
            'title': tag.name,
            'subtitle': '',
            'badge': f"{count} entrée{'s' if count != 1 else ''}" if count else '',
            'icon': tag.icon or '🏷️',
            'color': tag.color or '#6366f1',
            'url': reverse('tags:list'),
        })
    return items


GROUPS = (
    ('entries', search_entries),
    ('persons', search_persons),
    ('tags', search_tags),
)


def collect_results(user, query, limit=MAX_PER_GROUP):
    """Grouped results shared by the JSON API and the HTML page."""
    query = (query or '').strip()
    if not query:
        return []

    groups = []
    for key, builder in GROUPS:
        try:
            items = builder(user, query, limit)
        except Exception:  # pragma: no cover - defensive
            items = []
        if items:
            groups.append({'key': key, 'items': items})
    return groups


@login_required
def search_api(request):
    """Live suggestions for the navbar omnibox."""
    query = request.GET.get('q', '')
    try:
        limit = max(1, min(int(request.GET.get('limit', MAX_PER_GROUP)), 20))
    except (TypeError, ValueError):
        limit = MAX_PER_GROUP

    groups = collect_results(request.user, query, limit)
    return JsonResponse({
        'query': query.strip(),
        'total': sum(len(group['items']) for group in groups),
        'groups': groups,
    })


@method_decorator(login_required, name='dispatch')
class SearchResultsView(View):
    """Full results page — what the omnibox submits to on Enter."""

    def get(self, request):
        query = request.GET.get('q', '').strip()
        groups = collect_results(request.user, query, RESULTS_PER_GROUP)
        return render(request, 'search/results.html', {
            'query': query,
            'groups': groups,
            'total': sum(len(group['items']) for group in groups),
        })
