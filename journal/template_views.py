"""
MemoAi — Journal Template Views
HTML interface for journal entries.
"""

import json
import logging
import threading
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from .models import JournalEntry

logger = logging.getLogger('memoai')

MOOD_EMOJIS = {
    'amazing': '🤩', 'good': '😊', 'neutral': '😐', 'sad': '😢',
    'stressed': '😤', 'anxious': '😰', 'tired': '😴',
    'angry': '😠', 'excited': '🎉', 'grateful': '🙏',
}

# ───────────────────────────────────────────────────────────────────────────
# Immersive memories ("film de souvenirs")
# ───────────────────────────────────────────────────────────────────────────

_MEMORY_MONTHS = {
    'fr': ('JANV.', 'FÉVR.', 'MARS', 'AVR.', 'MAI', 'JUIN', 'JUIL.', 'AOÛT', 'SEPT.', 'OCT.', 'NOV.', 'DÉC.'),
    'en': ('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'),
}

_MEMORY_QUOTES = {
    'fr': (
        "Il y a des jours qui ne font aucun bruit. Et pourtant, ils nous changent.",
        "Ce que vous avez traversé vous a mené jusqu'ici.",
        "La beauté était déjà là. Vous l'avez simplement regardée.",
        "Les plus petits instants font les plus longs voyages.",
        "Rien de ce que vous avez ressenti n'est perdu.",
    ),
    'en': (
        "Some days make no sound. And yet, they change us.",
        "What you walked through brought you here.",
        "Beauty was already there. You simply looked at it.",
        "The smallest moments make the longest journeys.",
        "Nothing you felt is lost.",
    ),
}

_MEMORY_FINAL_QUOTES = {
    'fr': "Tout ce que vous avez aimé est encore là.",
    'en': "Everything you loved is still here.",
}

_MEMORY_TILE_LAYOUT = (
    ('wide', 'tall', 'square'),
    ('tall', 'wide', 'portrait'),
    ('square', 'tall', 'wide'),
)

_MEMORY_GRID_CLASSES = ('tall', 'wide', 'square', 'portrait', 'wide', 'square', 'tall', 'wide')


def _memory_image_variant(url, width):
    """Ask Cloudinary for a light, auto-formatted version of a stored image.

    Pexels/other remote URLs are returned untouched; the original is already
    compressed and may be transformed by its own query string.
    """
    if not url:
        return ''
    if 'res.cloudinary.com' in url and '/image/upload/' in url:
        head, tail = url.split('/image/upload/', 1)
        return f'{head}/image/upload/c_limit,w_{int(width)},q_auto,f_auto/{tail}'
    return url


# ───────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────

def _prefs_for(user):
    try:
        from accounts.models import UserPreferences
        prefs, _ = UserPreferences.objects.get_or_create(user=user)
        return prefs
    except Exception:
        return None


def _clean_coord(value):
    """Parse a map coordinate posted by the editor; ``None`` when absent."""
    if value in (None, ''):
        return None
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None


def _run_in_background(func, *args):
    """Run an eager Celery task off the request thread so the POST returns fast."""
    def runner():
        try:
            func(*args)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning('Background AI task failed: %s', exc)
        finally:
            try:
                from django.db import connection
                connection.close()
            except Exception:
                pass

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()


def _launch_ai(entry):
    """Kick off the AI pipeline. Non-blocking when Celery runs eagerly."""
    try:
        from ai.tasks import analyze_entry
    except Exception as exc:
        logger.warning('AI trigger import failed: %s', exc)
        return

    entry.ai_status = 'processing'
    entry.ai_error_message = ''
    entry.save(update_fields=['ai_status', 'ai_error_message'])

    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        # Eager mode would block the HTTP response for several seconds.
        _run_in_background(analyze_entry, str(entry.id))
    else:
        try:
            task = analyze_entry.delay(str(entry.id))
            entry.ai_task_id = getattr(task, 'id', '') or ''
            entry.save(update_fields=['ai_task_id'])
        except Exception as exc:
            logger.warning('AI trigger failed: %s', exc)
            entry.ai_status = 'failed'
            entry.ai_error_message = str(exc)
            entry.save(update_fields=['ai_status', 'ai_error_message'])


def _upload_warning(request, count):
    is_en = str(getattr(request, 'LANGUAGE_CODE', 'fr')).lower().startswith('en')
    if is_en:
        return f"{count} file(s) could not be uploaded to Cloudinary. Please try again."
    return f"{count} fichier(s) n'ont pas pu être envoyés vers Cloudinary. Réessayez."


def _persist_uploaded_media(entry, files):
    """Upload dropped/uploaded files to Cloudinary and link them to the entry.

    Local disk is never used. Returns ``(saved_media, failure_count)`` so the
    caller can warn the user when the provider rejects a file.
    """
    from common.cloud_media import upload_media
    from media_app.models import Media

    saved = []
    failed = 0
    for f in files:
        content_type = (getattr(f, 'content_type', '') or '').lower()
        if content_type.startswith('image/'):
            media_type = 'IMAGE'
        elif content_type.startswith('audio/'):
            media_type = 'AUDIO'
        else:
            ext = str(getattr(f, 'name', '')).lower().rsplit('.', 1)[-1]
            media_type = 'AUDIO' if ext in ('mp3', 'wav', 'ogg', 'webm', 'm4a', 'mp4') else 'IMAGE'

        try:
            url, public_id = upload_media(f, media_type, entry.user_id)
        except Exception as exc:
            failed += 1
            logger.warning('Cloudinary media upload failed for entry %s: %s', entry.pk, exc)
            continue

        media = Media.objects.create(
            entry=entry,
            media_type=media_type,
            storage_url=url,
            cloudinary_public_id=public_id,
            mime_type=content_type,
            file_size=getattr(f, 'size', 0) or 0,
            original_filename=getattr(f, 'name', '')[:255],
            processing_status='pending' if media_type in ('IMAGE', 'AUDIO') else 'completed',
        )
        saved.append(media)
    return saved, failed


def _attach_cover_image(entry, url, alt=''):
    """Attach a chosen online photo (Pexels) to the entry as its cover image."""
    if not url:
        return False
    from media_app.models import Media
    Media.objects.create(
        entry=entry,
        media_type='IMAGE',
        storage_url=url.strip(),
        mime_type='image/jpeg',
        original_filename=(alt or 'photo')[:255],
        processing_status='completed',
    )
    return True


def _parse_face_data(raw):
    """Parse the client-side face-api.js payload: {index: {descriptors, boxes}}."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items()}
    except (ValueError, TypeError):
        logger.info('Could not parse face_data payload')
    return {}


def _link_client_faces(media, info, user, prefs):
    """Match client descriptors against known people and record detections."""
    from ai.services.face_recognition_service import (
        db_to_embedding, embedding_to_db, find_matching_person,
    )
    from persons.models import FaceDetection, Person

    descriptors = (info or {}).get('descriptors') or []
    boxes = (info or {}).get('boxes') or []
    if not descriptors:
        return 0

    known = list(
        Person.objects.filter(user=user, face_embedding__isnull=False)
        .exclude(face_embedding='').values('id', 'name', 'face_embedding')
    )
    for person in known:
        person['embedding'] = db_to_embedding(person['face_embedding'])

    auto_delete = bool(getattr(prefs, 'auto_delete_face_embeddings', False))
    created = 0

    for index, embedding in enumerate(descriptors):
        if not embedding:
            continue
        box = boxes[index] if index < len(boxes) else {}
        matched = find_matching_person(embedding, known)

        if matched:
            person = Person.objects.filter(pk=matched['id']).first()
            confidence = matched['confidence']
        elif not auto_delete:
            person = Person.objects.create(
                user=user, name='Inconnu', face_embedding=embedding_to_db(embedding),
            )
            known.append({'id': str(person.id), 'name': person.name, 'embedding': embedding})
            confidence = 1.0
        else:
            person = None
            confidence = 0.85

        FaceDetection.objects.create(
            media=media, person=person, confidence=confidence, bounding_box=box,
        )
        created += 1
    return created


def _handle_media_processing(entry, media_list, face_data):
    """Link client-detected faces, or fall back to server-side detection."""
    prefs = _prefs_for(entry.user)
    use_faces = bool(getattr(prefs, 'face_recognition_consent', False))

    for index, media in enumerate(media_list):
        if media.media_type == 'IMAGE':
            info = face_data.get(str(index))
            if use_faces and info and info.get('descriptors'):
                _link_client_faces(media, info, entry.user, prefs)
                from media_app.models import Media
                Media.objects.filter(pk=media.pk).update(processing_status='completed')
            elif getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
                try:
                    from ai.tasks import process_image_media
                    _run_in_background(process_image_media, str(media.id))
                except Exception as exc:
                    logger.warning('Face processing trigger failed: %s', exc)
            else:
                try:
                    from ai.tasks import process_image_media
                    process_image_media.delay(str(media.id))
                except Exception as exc:
                    logger.warning('Face processing trigger failed: %s', exc)

        elif media.media_type == 'AUDIO':
            if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
                try:
                    from ai.tasks import process_audio_media
                    _run_in_background(process_audio_media, str(media.id))
                except Exception as exc:
                    logger.warning('Audio processing trigger failed: %s', exc)
            else:
                try:
                    from ai.tasks import process_audio_media
                    process_audio_media.delay(str(media.id))
                except Exception as exc:
                    logger.warning('Audio processing trigger failed: %s', exc)


@login_required
def pexels_search(request):
    """JSON endpoint powering the online-photo picker in the journal editor."""
    from common import pexels

    query = request.GET.get('q', '')
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 24)
    orientation = request.GET.get('orientation', 'landscape')
    result = pexels.search_photos(query, per_page=per_page, page=page, orientation=orientation)
    result['thumbnails'] = [pexels.pick_thumbnail(p['url']) for p in result['photos']]
    return JsonResponse(result)


def _places_lang(request):
    """Nominatim returns localised labels — follow the UI language."""
    return 'en' if getattr(request, 'LANGUAGE_CODE', '') == 'en' else 'fr'


@login_required
def place_search(request):
    """JSON endpoint powering the "Add a location" autocomplete."""
    from common import places

    query = request.GET.get('q', '')
    result = places.search_places(query, limit=6, lang=_places_lang(request))
    return JsonResponse(result)


@login_required
def place_reverse(request):
    """Resolve a map pin into a readable place name."""
    from common import places

    result = places.reverse_place(
        request.GET.get('lat'), request.GET.get('lon'), lang=_places_lang(request)
    )
    return JsonResponse(result)


@login_required
def ai_status(request, pk):
    """Poll the AI processing state of one entry (used by the detail page)."""
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    analysis = getattr(entry, 'ai_analysis', None)
    payload = {
        'status': entry.ai_status,
        'error': entry.ai_error_message,
        'summary': getattr(analysis, 'summary', '') if analysis else '',
        'sentiment': getattr(analysis, 'sentiment', '') if analysis else '',
        'sentiment_score': getattr(analysis, 'sentiment_score', None) if analysis else None,
        'mood_insight': getattr(analysis, 'mood_insight', '') if analysis else '',
        'keywords': getattr(analysis, 'keywords', []) if analysis else [],
        'generated_image_url': getattr(analysis, 'generated_image_url', '') if analysis else '',
        'image_generation_status': getattr(analysis, 'image_generation_status', '') if analysis else '',
    }
    return JsonResponse(payload)


@method_decorator(login_required, name='dispatch')
class HomeView(View):
    """Dashboard / home page."""

    def get(self, request):
        today = timezone.now().date()

        today_entry = JournalEntry.objects.filter(
            user=request.user, entry_date=today
        ).order_by('-created_at').first()

        on_this_day = JournalEntry.objects.filter(
            user=request.user,
            entry_date__month=today.month,
            entry_date__day=today.day,
        ).exclude(entry_date=today).order_by('-entry_date')[:5]

        recent_entries = JournalEntry.objects.filter(
            user=request.user
        ).prefetch_related('media', 'tags').select_related('ai_analysis').order_by('-entry_date')[:6]

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

        # Animated hero collage: the user's own covers, newest first.
        hero_photos = []
        for e in JournalEntry.objects.filter(user=request.user).prefetch_related('media').order_by('-entry_date')[:40]:
            url = e.cover_image_url
            if url and url not in hero_photos:
                hero_photos.append(url)
            if len(hero_photos) >= 9:
                break

        return render(request, 'journal/home.html', {
            'today': today,
            'today_entry': today_entry,
            'on_this_day': on_this_day,
            'recent_entries': recent_entries,
            'stats': stats,
            'hero_photos': hero_photos,
        })


@method_decorator(login_required, name='dispatch')
class MemoryExperienceView(View):
    """Immersive, auto-scrolling film built from every image of the account.

    Images come from the journal (uploaded photos + AI illustrations) and from
    the people's portraits. Nothing is mocked: an account with no image gets a
    dedicated empty state.
    """

    def get(self, request):
        from persons.models import Person

        prefs = getattr(request.user, 'preferences', None)
        lang = 'en' if str(getattr(prefs, 'language', 'fr') or 'fr').lower().startswith('en') else 'fr'
        months = _MEMORY_MONTHS[lang]

        entries = list(
            JournalEntry.objects.filter(user=request.user)
            .select_related('ai_analysis')
            .prefetch_related('media')
            .order_by('-entry_date', '-created_at')
        )

        photos = []
        seen = set()

        def add_photo(url, *, title='', date_value=None, sort_dt=None, kind='photo', entry_id=None):
            url = (url or '').strip()
            if not url or url in seen:
                return
            seen.add(url)
            when = date_value or timezone.localdate()
            photos.append({
                'url': url,
                'large_url': _memory_image_variant(url, 1700),
                'thumb_url': _memory_image_variant(url, 800),
                'title': (title or '').strip(),
                'date': when,
                'sort_dt': sort_dt or timezone.now(),
                'date_label': f'{months[when.month - 1]} {when.year}',
                'year': when.year,
                'kind': kind,
                'entry_id': str(entry_id) if entry_id else '',
            })

        for entry in entries:
            for media in entry.media.all():
                if media.media_type not in ('IMAGE', 'GENERATED_IMAGE'):
                    continue
                add_photo(
                    media.storage_url,
                    title=entry.title,
                    date_value=entry.entry_date,
                    sort_dt=entry.created_at,
                    kind='illustration' if media.media_type == 'GENERATED_IMAGE' else 'photo',
                    entry_id=entry.pk,
                )

            analysis = getattr(entry, 'ai_analysis', None)
            if analysis and analysis.generated_image_url:
                add_photo(
                    analysis.generated_image_url,
                    title=entry.title,
                    date_value=entry.entry_date,
                    sort_dt=entry.created_at,
                    kind='illustration',
                    entry_id=entry.pk,
                )

        for person in (
            Person.objects.filter(user=request.user)
            .exclude(avatar_url='')
            .order_by('-created_at')
        ):
            add_photo(
                person.avatar_url,
                title=person.name,
                date_value=person.created_at.date(),
                sort_dt=person.created_at,
                kind='portrait',
            )

        photos.sort(key=lambda item: (item['date'], item['sort_dt']), reverse=True)
        for index, photo in enumerate(photos, 1):
            photo['number'] = f'{index:03d}'
            photo['grid_class'] = _MEMORY_GRID_CLASSES[(index - 1) % len(_MEMORY_GRID_CLASSES)]

        # Screenshot-like hero wall: three staggered columns, mixed tile sizes.
        hero_photos = photos[:9]
        hero_columns = []
        for col_index in range(3):
            column = []
            for slot, photo_index in enumerate(range(col_index, len(hero_photos), 3)):
                photo = dict(hero_photos[photo_index])
                photo['tile'] = _MEMORY_TILE_LAYOUT[col_index][min(slot, 2)]
                photo['tagged'] = slot == 0
                column.append(photo)
            if column:
                hero_columns.append(column)

        # Remaining images become alternating editorial scenes.
        remaining = photos[9:]
        quotes = _MEMORY_QUOTES[lang]
        scenes = []
        for scene_index, start in enumerate(range(0, len(remaining), 3)):
            scenes.append({
                'photos': remaining[start:start + 3],
                'side': 'right' if scene_index % 2 == 0 else 'left',
                'quote': quotes[scene_index % len(quotes)],
            })

        years = {entry.entry_date.year for entry in entries} | {photo['year'] for photo in photos}
        ordered_years = sorted(years)
        if len(ordered_years) > 1:
            period = f'{ordered_years[0]}—{ordered_years[-1]}'
        elif ordered_years:
            period = str(ordered_years[-1])
        else:
            period = str(timezone.localdate().year)

        return render(request, 'journal/memory_experience.html', {
            'photos': photos,
            'hero_columns': hero_columns,
            'scenes': scenes,
            'photo_count': len(photos),
            'entry_count': len(entries),
            'period': period,
            'final_quote': _MEMORY_FINAL_QUOTES[lang],
            'memory_mode': True,
        })


@method_decorator(login_required, name='dispatch')
class EntryListView(View):
    """Paginated list with search and filters."""

    def get(self, request):
        qs = JournalEntry.objects.filter(
            user=request.user
        ).prefetch_related('media', 'tags').select_related('ai_analysis').order_by('-entry_date')

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
        latitude = _clean_coord(request.POST.get('latitude'))
        longitude = _clean_coord(request.POST.get('longitude'))
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
            latitude=latitude,
            longitude=longitude,
            entry_date=entry_date_str,
        )

        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids, user=request.user)
            entry.tags.set(tags)

        media_list, upload_failures = _persist_uploaded_media(entry, request.FILES.getlist('media_files'))
        _attach_cover_image(entry, request.POST.get('cover_image_url', ''),
                            request.POST.get('cover_image_alt', ''))
        _handle_media_processing(entry, media_list, _parse_face_data(request.POST.get('face_data')))

        if upload_failures:
            messages.warning(request, _upload_warning(request, upload_failures))

        if content:
            _launch_ai(entry)

        messages.success(request, 'Entrée créée — l\'IA analyse votre journée.')
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
                'latitude': {'value': entry.latitude},
                'longitude': {'value': entry.longitude},
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
        posted_lat = _clean_coord(request.POST.get('latitude'))
        posted_lon = _clean_coord(request.POST.get('longitude'))
        if posted_lat is not None and posted_lon is not None:
            entry.latitude = posted_lat
            entry.longitude = posted_lon
        else:
            entry.latitude = None
            entry.longitude = None
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

        media_list, upload_failures = _persist_uploaded_media(entry, request.FILES.getlist('media_files'))
        _attach_cover_image(entry, request.POST.get('cover_image_url', ''),
                            request.POST.get('cover_image_alt', ''))
        _handle_media_processing(entry, media_list, _parse_face_data(request.POST.get('face_data')))

        if upload_failures:
            messages.warning(request, _upload_warning(request, upload_failures))

        if entry.content:
            _launch_ai(entry)

        messages.success(request, 'Entrée modifiée — l\'IA réanalyse votre journée.')
        return redirect('journal:detail', pk=entry.pk)


@login_required
def entry_delete(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Entrée supprimée.')
        return redirect('journal:list')
    return redirect('journal:detail', pk=pk)


@login_required
def trigger_ai_template(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        _launch_ai(entry)
        messages.success(request, 'Analyse IA lancée.')
    return redirect('journal:detail', pk=pk)
