"""
MemoAi — one-shot migration of legacy local media files to Cloudinary.

Before this release, journal photos/audio, portraits, profile avatars and a
few AI illustrations were written under ``MEDIA_ROOT``. Every asset must now
live on Cloudinary. This command scans the database for ``/media/...`` URLs,
uploads each backing file, rewrites the URL, and (unless ``--keep-local``)
removes the local copy only after a successful upload.

Usage:
    python manage.py migrate_local_media [--dry-run] [--keep-local]
"""

from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from common.cloud_media import CloudinaryMediaError, upload_file


class Command(BaseCommand):
    help = 'Upload locally stored media to Cloudinary and rewrite database URLs.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only list what would be migrated.')
        parser.add_argument('--keep-local', action='store_true', help='Do not delete local files after upload.')

    # ── helpers ────────────────────────────────────────────────────────────

    def _local_path(self, url: str) -> Path | None:
        media_url = settings.MEDIA_URL or '/media/'
        if not url or not url.startswith(media_url):
            return None
        relative = url[len(media_url):].split('?', 1)[0]
        candidate = (Path(settings.MEDIA_ROOT) / relative).resolve()
        try:
            candidate.relative_to(Path(settings.MEDIA_ROOT).resolve())
        except ValueError:
            return None
        return candidate

    def _delete_local(self, path: Path, keep: bool):
        if keep or not path.exists():
            return
        try:
            os.remove(path)
        except OSError as exc:
            self.stderr.write(self.style.WARNING(f'  ! could not delete {path}: {exc}'))
            return
        # Prune now-empty month/day folders but never MEDIA_ROOT itself.
        parent = path.parent
        root = Path(settings.MEDIA_ROOT).resolve()
        while parent.resolve() != root and parent.exists():
            try:
                next(parent.iterdir())
                break
            except StopIteration:
                parent.rmdir()
                parent = parent.parent

    def _migrate(self, label, url, folder, resource_type, keep, dry_run, update):
        path = self._local_path(url)
        if path is None:
            return False

        # The same backing file can be referenced twice (Media row + AIAnalysis).
        # Reuse the Cloudinary URL produced earlier in this run.
        if url in getattr(self, '_seen', {}):
            update(self._seen[url], '')
            self.stdout.write(self.style.SUCCESS(f'  [ok] {label}: reused existing Cloudinary URL'))
            return False

        if not path.exists():
            self.stderr.write(self.style.WARNING(f'  ! {label}: file missing on disk, skipped ({url})'))
            return False
        if dry_run:
            self.stdout.write(f'  -> would upload {path} to {folder}')
            return False

        with open(path, 'rb') as handle:
            new_url, public_id = upload_file(handle, folder, resource_type=resource_type)
        self._seen = getattr(self, '_seen', {})
        self._seen[url] = new_url
        update(new_url, public_id)
        self._delete_local(path, keep)
        self.stdout.write(self.style.SUCCESS(f'  [ok] {label}: {new_url}'))
        return True

    # ── command entry point ────────────────────────────────────────────────

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        keep = options['keep_local']

        from media_app.models import Media
        from persons.models import Person
        from accounts.models import User

        media_url = settings.MEDIA_URL or '/media/'
        uploaded = 0

        self.stdout.write(self.style.MIGRATE_HEADING('Journal media'))
        for media in Media.objects.filter(storage_url__startswith=media_url):
            kind = 'AUDIO' if media.media_type == 'AUDIO' else 'IMAGE'
            subfolder = 'audio' if kind == 'AUDIO' else 'images'
            if media.media_type == 'GENERATED_IMAGE':
                folder = f'generated/{media.entry.user_id}'
            else:
                folder = f'journal/{media.entry.user_id}/{subfolder}'

            def update(url, public_id, media=media):
                media.storage_url = url
                media.cloudinary_public_id = public_id
                media.save(update_fields=['storage_url', 'cloudinary_public_id'])

            resource_type = 'video' if kind == 'AUDIO' else 'image'
            if self._migrate(f'Media {media.id} ({media.media_type})', media.storage_url,
                             folder, resource_type, keep, dry_run, update):
                uploaded += 1

        self.stdout.write(self.style.MIGRATE_HEADING('Person portraits'))
        for person in Person.objects.filter(avatar_url__startswith=media_url):
            def update(url, public_id, person=person):
                person.avatar_url = url
                person.save(update_fields=['avatar_url'])

            if self._migrate(f'Person {person.id} ({person.name})', person.avatar_url,
                             f'persons/{person.user_id}', 'image', keep, dry_run, update):
                uploaded += 1

        self.stdout.write(self.style.MIGRATE_HEADING('Profile avatars'))
        for user in User.objects.filter(avatar__startswith=media_url):
            def update(url, public_id, user=user):
                user.avatar = url
                user.save(update_fields=['avatar'])

            if self._migrate(f'User {user.id} ({user.email})', user.avatar,
                             f'avatars/{user.id}', 'image', keep, dry_run, update):
                uploaded += 1

        self.stdout.write(self.style.MIGRATE_HEADING('AI generated illustrations'))
        try:
            from ai.models import AIAnalysis
        except Exception:
            AIAnalysis = None
        if AIAnalysis is not None:
            for analysis in AIAnalysis.objects.filter(generated_image_url__startswith=media_url).select_related('entry'):
                local_path = self._local_path(analysis.generated_image_url)
                if local_path is not None and not local_path.exists():
                    # The backing file may already have been migrated through
                    # its Media row and deleted. Reuse that Cloudinary URL.
                    sibling = (
                        Media.objects
                        .filter(entry=analysis.entry, media_type='GENERATED_IMAGE')
                        .exclude(storage_url__startswith=media_url)
                        .first()
                    )
                    if sibling is not None:
                        analysis.generated_image_url = sibling.storage_url
                        analysis.save(update_fields=['generated_image_url'])
                        self.stdout.write(self.style.SUCCESS(
                            f'  [ok] Analysis {analysis.id}: reused {sibling.storage_url}'))
                        continue

                def update(url, public_id, analysis=analysis):
                    analysis.generated_image_url = url
                    analysis.save(update_fields=['generated_image_url'])

                if self._migrate(f'Analysis {analysis.id}', analysis.generated_image_url,
                                 f'generated/{analysis.entry.user_id}', 'image',
                                 keep, dry_run, update):
                    uploaded += 1

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — nothing changed.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Done — {uploaded} file(s) migrated to Cloudinary.'))
