"""
MemoAi — Cloudinary media gateway.

Every user asset (journal photos, audio notes, portraits, profile avatars and
AI illustrations) is uploaded to Cloudinary. There is deliberately **no local
disk fallback**: if the provider is not configured or rejects an upload, the
caller gets an exception and can surface a real error instead of silently
writing to ``MEDIA_ROOT``.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger('memoai')


class CloudinaryMediaError(RuntimeError):
    """Raised when an asset cannot be stored on Cloudinary."""


# ───────────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────────

def _credentials() -> tuple[str, str, str]:
    config = getattr(settings, 'CLOUDINARY_STORAGE', {}) or {}
    cloud_name = str(config.get('CLOUD_NAME') or '').strip()
    api_key = str(config.get('API_KEY') or '').strip()
    api_secret = str(config.get('API_SECRET') or '').strip()
    if not (cloud_name and api_key and api_secret):
        raise CloudinaryMediaError(
            'Cloudinary is not configured: set CLOUDINARY_CLOUD_NAME, '
            'CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET.'
        )
    return cloud_name, api_key, api_secret


def is_configured() -> bool:
    try:
        _credentials()
    except CloudinaryMediaError:
        return False
    return True


def _configure() -> Any:
    """Configure the Cloudinary SDK and return the ``cloudinary`` module."""
    import cloudinary

    cloud_name, api_key, api_secret = _credentials()
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )
    return cloudinary


def _root() -> str:
    return str(getattr(settings, 'CLOUDINARY_MEDIA_FOLDER', 'memoai') or 'memoai').strip('/')


# ───────────────────────────────────────────────────────────────────────────
# Upload helpers
# ───────────────────────────────────────────────────────────────────────────

def upload_file(
    file,
    folder: str = '',
    *,
    resource_type: str = 'image',
    public_id: str = '',
    use_filename: bool = True,
    unique_filename: bool = True,
) -> tuple[str, str]:
    """
    Upload ``file`` to ``<CLOUDINARY_MEDIA_FOLDER>/<folder>``.

    Returns ``(secure_url, public_id)`` and raises :class:`CloudinaryMediaError`
    when Cloudinary is unavailable or returns an unusable payload.
    """
    import cloudinary.uploader

    _configure()

    full_folder = '/'.join(part.strip('/') for part in (_root(), folder) if part and part.strip('/'))
    options: dict[str, Any] = {
        'folder': full_folder,
        'resource_type': resource_type,
        'overwrite': False,
        'use_filename': use_filename,
        'unique_filename': unique_filename,
        'timeout': 120,
    }
    if public_id:
        options['public_id'] = public_id

    try:
        result = cloudinary.uploader.upload(file, **options)
    except Exception as exc:  # pragma: no cover - network/provider failure
        logger.error('Cloudinary upload failed (folder=%s): %s', full_folder, exc)
        raise CloudinaryMediaError(f'Cloudinary upload failed: {exc}') from exc

    url = result.get('secure_url') or result.get('url')
    if not url:
        raise CloudinaryMediaError('Cloudinary returned no URL for the uploaded file.')
    return url, result.get('public_id', '')


def upload_media(file, media_type: str, user_id, kind: str | None = 'journal') -> tuple[str, str]:
    """Upload a journal photo/audio note and return ``(url, public_id)``."""
    is_audio = str(media_type).upper() == 'AUDIO'
    subfolder = 'audio' if is_audio else 'images'
    folder = f'{kind}/{user_id}/{subfolder}' if kind else f'{user_id}/{subfolder}'
    return upload_file(
        file,
        folder,
        resource_type='video' if is_audio else 'image',
    )


def upload_avatar(file, user_id, kind: str = 'avatars') -> str:
    """Upload a portrait/avatar and return its Cloudinary secure URL."""
    validate_image(file)
    url, _ = upload_file(file, f'{kind}/{user_id}', resource_type='image')
    return url


# ───────────────────────────────────────────────────────────────────────────
# Read helpers
# ───────────────────────────────────────────────────────────────────────────

def image_variant(url: str, width: int) -> str:
    """Return a lighter, auto-formatted variant of a stored image URL.

    Cloudinary URLs get a ``c_limit,w_…,q_auto,f_auto`` transformation so the
    grids download small files; any other remote URL (Pexels, ...) is returned
    untouched because it is already optimised and may carry its own query.
    """
    if not url:
        return ''
    if 'res.cloudinary.com' in url and '/image/upload/' in url:
        head, tail = url.split('/image/upload/', 1)
        return f'{head}/image/upload/c_limit,w_{int(width)},q_auto,f_auto/{tail}'
    return url


# ───────────────────────────────────────────────────────────────────────────
# Validation
# ───────────────────────────────────────────────────────────────────────────

def validate_image(file) -> None:
    """Reject non-images and oversized files before hitting the network."""
    content_type = (getattr(file, 'content_type', '') or '').lower()
    allowed = set(getattr(settings, 'ALLOWED_IMAGE_TYPES', [
        'image/jpeg', 'image/png', 'image/webp', 'image/gif',
    ]))
    if content_type and content_type not in allowed:
        raise CloudinaryMediaError(f'Unsupported image type: {content_type}')

    max_size = int(getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024))
    if getattr(file, 'size', 0) > max_size:
        raise CloudinaryMediaError('File too large.')
