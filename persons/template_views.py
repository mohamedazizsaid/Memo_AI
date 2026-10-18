"""
MemoAi — Persons Template Views
HTML interface for people management.
"""

import logging
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View

from .models import Person

logger = logging.getLogger('memoai')


@method_decorator(login_required, name='dispatch')
class PersonListView(View):
    def get(self, request):
        persons = Person.objects.filter(user=request.user)
        try:
            from accounts.models import UserPreferences
            prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
            consent_granted = prefs.face_recognition_consent
        except Exception:
            consent_granted = False

        return render(request, 'persons/list.html', {
            'persons': persons,
            'consent_granted': consent_granted,
        })


@method_decorator(login_required, name='dispatch')
class PersonDetailView(View):
    def get(self, request, pk):
        person = get_object_or_404(Person, pk=pk, user=request.user)

        # Find journal entries where this person appears
        from journal.models import JournalEntry
        entries = JournalEntry.objects.filter(
            user=request.user,
            media__face_detections__person=person
        ).distinct().prefetch_related('media', 'tags').select_related('ai_analysis')[:12]

        return render(request, 'persons/detail.html', {
            'person': person,
            'entries': entries,
        })


@method_decorator(login_required, name='dispatch')
class PersonCreateView(View):
    def get(self, request):
        return render(request, 'persons/form.html', {'person': None})

    def post(self, request):
        name = request.POST.get('name', '').strip() or 'Inconnu'
        notes = request.POST.get('notes', '').strip()
        avatar_url = request.POST.get('avatar_url', '').strip()
        person = Person.objects.create(user=request.user, name=name, notes=notes, avatar_url=avatar_url)
        messages.success(request, f'Personne "{name}" ajoutee.')
        return redirect('persons:detail', pk=person.pk)


@method_decorator(login_required, name='dispatch')
class PersonEditView(View):
    def get(self, request, pk):
        person = get_object_or_404(Person, pk=pk, user=request.user)
        return render(request, 'persons/form.html', {'person': person})

    def post(self, request, pk):
        person = get_object_or_404(Person, pk=pk, user=request.user)
        person.name = request.POST.get('name', person.name).strip()
        person.notes = request.POST.get('notes', person.notes).strip()
        person.avatar_url = request.POST.get('avatar_url', person.avatar_url).strip()
        person.save()
        messages.success(request, 'Personne modifiee.')
        return redirect('persons:detail', pk=person.pk)


@login_required
def person_delete(request, pk):
    person = get_object_or_404(Person, pk=pk, user=request.user)
    if request.method == 'POST':
        name = person.name
        person.delete()
        messages.success(request, f'"{name}" a ete supprime.')
        return redirect('persons:list')
    return redirect('persons:detail', pk=pk)
