"""
MemoAi — Persons Template Views
HTML interface for people management, with photo upload + face descriptors.
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from .models import Person

logger = logging.getLogger('memoai')

PERSONS_PER_PAGE = 12


def _save_avatar(user, avatar_file):
    """Upload an uploaded portrait to Cloudinary and return its secure URL.

    The local disk is never touched (see ``common.cloud_media``). Raises on
    provider/configuration errors so the view can keep the old photo.
    """
    from common.cloud_media import upload_avatar

    return upload_avatar(avatar_file, user.id, kind='persons')


def _avatar_warning(request, editing=False):
    is_en = str(getattr(request, 'LANGUAGE_CODE', 'fr')).lower().startswith('en')
    if editing:
        return ('The new photo could not be uploaded to Cloudinary. '
                'The previous photo was kept.') if is_en else (
            "La nouvelle photo n'a pas pu être envoyée vers Cloudinary. "
            "L'ancienne photo a été conservée.")
    return ('The photo could not be uploaded to Cloudinary. '
            'The person was saved without a photo.') if is_en else (
        "La photo n'a pas pu être envoyée vers Cloudinary. "
        "La personne a été enregistrée sans photo.")


def _extract_descriptor(request):
    """Read the client-side face-api.js descriptor for the uploaded photo."""
    raw = request.POST.get('face_descriptor', '').strip()
    if not raw:
        return ''
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return ''
    if isinstance(data, dict):
        data = data.get('descriptor') or data.get('descriptors') or []
        if data and isinstance(data[0], list):
            data = data[0]
    if isinstance(data, list) and data:
        from ai.services.face_recognition_service import embedding_to_db
        return embedding_to_db(data)
    return ''


@method_decorator(login_required, name='dispatch')
class PersonListView(View):
    def get(self, request):
        persons = Person.objects.filter(user=request.user).order_by('name')
        try:
            from accounts.models import UserPreferences
            prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
            consent_granted = prefs.face_recognition_consent
        except Exception:
            consent_granted = False

        paginator = Paginator(persons, PERSONS_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        return render(request, 'persons/list.html', {
            'persons': page_obj,
            'page_obj': page_obj,
            'is_paginated': paginator.num_pages > 1,
            'consent_granted': consent_granted,
        })


@method_decorator(login_required, name='dispatch')
class PersonDetailView(View):
    def get(self, request, pk):
        person = get_object_or_404(Person, pk=pk, user=request.user)

        from journal.models import JournalEntry
        entries = JournalEntry.objects.filter(
            user=request.user,
            media__face_detections__person=person
        ).distinct().prefetch_related('media', 'tags').select_related('ai_analysis').order_by('-entry_date')

        paginator = Paginator(entries, PERSONS_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        face_detections = person.face_detections.select_related('media', 'media__entry').order_by('-created_at')[:8]

        return render(request, 'persons/detail.html', {
            'person': person,
            'entries': page_obj,
            'page_obj': page_obj,
            'is_paginated': paginator.num_pages > 1,
            'face_detections': face_detections,
        })


@method_decorator(login_required, name='dispatch')
class PersonCreateView(View):
    def get(self, request):
        return render(request, 'persons/form.html', {'person': None})

    def post(self, request):
        name = request.POST.get('name', '').strip()
        notes = request.POST.get('notes', '').strip()

        # Server-side guard mirroring the inline validation (JS can be off).
        if len(name) < 2:
            return render(request, 'persons/form.html', {
                'person': None,
                'entered_name': name,
                'entered_notes': notes,
                'name_error': True,
            }, status=400)

        # The portrait can only come from the drag & drop zone now — the old
        # "paste a photo URL" field is gone.
        avatar_url = ''
        avatar_file = request.FILES.get('avatar_file')
        if avatar_file:
            try:
                avatar_url = _save_avatar(request.user, avatar_file)
            except Exception as exc:
                logger.warning('Cloudinary portrait upload failed: %s', exc)
                messages.warning(request, _avatar_warning(request))

        person = Person.objects.create(
            user=request.user, name=name, notes=notes, avatar_url=avatar_url,
            face_embedding=_extract_descriptor(request) or None,
        )
        if person.face_embedding:
            messages.success(request, f'Personne « {name} » ajoutée avec sa reconnaissance faciale.')
        else:
            messages.success(request, f'Personne « {name} » ajoutée.')
        return redirect('persons:detail', pk=person.pk)


@method_decorator(login_required, name='dispatch')
class PersonEditView(View):
    def get(self, request, pk):
        person = get_object_or_404(Person, pk=pk, user=request.user)
        return render(request, 'persons/form.html', {'person': person})

    def post(self, request, pk):
        person = get_object_or_404(Person, pk=pk, user=request.user)
        new_name = request.POST.get('name', '').strip()
        new_notes = request.POST.get('notes', person.notes).strip()

        if len(new_name) < 2:
            return render(request, 'persons/form.html', {
                'person': person,
                'entered_name': new_name,
                'entered_notes': new_notes,
                'name_error': True,
            }, status=400)

        person.name = new_name
        person.notes = new_notes

        avatar_file = request.FILES.get('avatar_file')
        if avatar_file:
            try:
                person.avatar_url = _save_avatar(request.user, avatar_file)
            except Exception as exc:
                logger.warning('Cloudinary portrait upload failed: %s', exc)
                messages.warning(request, _avatar_warning(request, editing=True))

        descriptor = _extract_descriptor(request)
        if descriptor:
            person.face_embedding = descriptor
            person.save(update_fields=['name', 'notes', 'avatar_url', 'face_embedding'])
            messages.success(request, 'Personne modifiée avec sa reconnaissance faciale.')
        else:
            person.save()
            messages.success(request, 'Personne modifiée.')
        return redirect('persons:detail', pk=person.pk)


@login_required
def person_delete(request, pk):
    person = get_object_or_404(Person, pk=pk, user=request.user)
    if request.method == 'POST':
        name = person.name
        person.delete()
        messages.success(request, f'« {name} » a été supprimé.')
        return redirect('persons:list')
    return redirect('persons:detail', pk=pk)
