"""
MemoAI — Pexels photo search service.

Used by the journal editor so people can pick a real photo instead of waiting
for the AI to generate one. No third-party SDK: plain HTTPS via ``requests``.

If ``PEXELS_API_KEY`` is empty the functions return an empty list and set a
``reason`` so the UI can explain what to do — the rest of the app keeps working.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger('memoai')

TIMEOUT = 12


def is_configured() -> bool:
    return bool(getattr(settings, 'PEXELS_API_KEY', ''))


def _headers():
    return {'Authorization': settings.PEXELS_API_KEY}


def _simplify(photo: dict) -> dict:
    src = photo.get('src', {}) or {}
    return {
        'id': photo.get('id'),
        'url': src.get('large') or src.get('large2x') or src.get('original') or '',
        'thumb': src.get('medium') or src.get('small') or src.get('tiny') or '',
        'alt': (photo.get('alt') or '').strip(),
        'photographer': photo.get('photographer') or '',
        'width': photo.get('width') or 0,
        'height': photo.get('height') or 0,
    }


def search_photos(query: str = '', per_page: int = 24, page: int = 1,
                  orientation: str = 'landscape') -> dict:
    """Search Pexels. Returns ``{photos, total, configured, reason}``."""
    if not is_configured():
        return {'photos': [], 'total': 0, 'configured': False,
                'reason': 'missing_key'}

    query = (query or '').strip()
    endpoint = f"{settings.PEXELS_API_BASE_URL.rstrip('/')}/{'search' if query else 'curated'}"
    params = {'per_page': max(1, min(int(per_page or 24), 40)), 'page': max(1, int(page or 1))}
    if query:
        params['query'] = query
    if orientation in ('landscape', 'portrait', 'square'):
        params['orientation'] = orientation

    try:
        resp = requests.get(endpoint, headers=_headers(), params=params, timeout=TIMEOUT)
        if resp.status_code == 401:
            return {'photos': [], 'total': 0, 'configured': True, 'reason': 'invalid_key'}
        resp.raise_for_status()
        data = resp.json()
        return {
            'photos': [_simplify(p) for p in data.get('photos', [])],
            'total': data.get('total_results', len(data.get('photos', []))),
            'configured': True,
            'reason': '',
        }
    except requests.RequestException as exc:
        logger.warning('Pexels search failed: %s', exc)
        return {'photos': [], 'total': 0, 'configured': True, 'reason': 'network'}


def pick_thumbnail(url: str) -> str:
    """Best-effort square-ish thumbnail from a Pexels large URL."""
    if not url:
        return ''
    # Pexels CDN accepts ?auto=compress&cs=tinysrgb&w= &h= &fit=crop
    sep = '&' if '?' in url else '?'
    return f"{url}{sep}auto=compress&cs=tinysrgb&w=400"
