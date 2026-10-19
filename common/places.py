"""
MemoAI — Place lookup service.

Powers the "Add a location" field of the journal editor: type a name and pick
a real place, or drop a pin on the map. Backed by OpenStreetMap's Nominatim,
which is free and needs no API key.

Nominatim's usage policy asks for a real User-Agent, a low request rate and no
bulk geocoding — so every response is memoised for a few minutes and the
function returns a small ``reason`` instead of raising when the network is
unavailable.
"""

from __future__ import annotations

import logging
import threading
import time
from urllib.parse import urlencode

import requests
from django.conf import settings

logger = logging.getLogger('memoai')

TIMEOUT = 10
CACHE_TTL = 300          # seconds
CACHE_MAX = 400          # entries

# Nominatim requires identifying the application.
USER_AGENT = 'MemoAI/1.0 (personal journal; contact: memoai@localhost)'

_cache: dict = {}
_cache_lock = threading.Lock()


def _base_url() -> str:
    return getattr(
        settings, 'PLACES_API_BASE_URL',
        'https://nominatim.openstreetmap.org',
    ).rstrip('/')


def _headers() -> dict:
    return {'User-Agent': USER_AGENT, 'Accept': 'application/json'}


def _cache_get(key):
    with _cache_lock:
        hit = _cache.get(key)
        if not hit:
            return None
        if time.time() - hit[0] > CACHE_TTL:
            _cache.pop(key, None)
            return None
        return hit[1]


def _cache_put(key, value):
    with _cache_lock:
        if len(_cache) >= CACHE_MAX:
            _cache.clear()
        _cache[key] = (time.time(), value)


def _simplify(item: dict) -> dict:
    display = (item.get('display_name') or '').strip()
    parts = [p.strip() for p in display.split(',') if p.strip()]
    name = parts[0] if parts else display
    return {
        'label': display,
        'name': name,
        'lat': float(item.get('lat') or 0),
        'lon': float(item.get('lon') or 0),
        'type': (item.get('type') or item.get('class') or '').strip(),
    }


def search_places(query: str = '', limit: int = 6, lang: str = 'fr') -> dict:
    """Free-text place search. Returns ``{places, reason}``."""
    query = (query or '').strip()
    if len(query) < 2:
        return {'places': [], 'reason': 'too_short'}

    limit = max(1, min(int(limit or 6), 10))
    cache_key = f'search:{lang}:{limit}:{query.lower()}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = {
        'q': query,
        'format': 'jsonv2',
        'addressdetails': 0,
        'limit': limit,
        'accept-language': lang or 'fr',
    }
    try:
        resp = requests.get(
            f'{_base_url()}/search', params=params,
            headers=_headers(), timeout=TIMEOUT,
        )
        resp.raise_for_status()
        payload = [_simplify(item) for item in resp.json()]
        result = {'places': payload, 'reason': ''}
    except requests.RequestException as exc:
        logger.warning('Place search failed: %s', exc)
        result = {'places': [], 'reason': 'network'}
    except (ValueError, TypeError) as exc:
        logger.warning('Place search returned invalid JSON: %s', exc)
        result = {'places': [], 'reason': 'network'}

    _cache_put(cache_key, result)
    return result


def reverse_place(lat: float, lon: float, lang: str = 'fr') -> dict:
    """Turn coordinates picked on the map into a readable label."""
    try:
        lat = round(float(lat), 5)
        lon = round(float(lon), 5)
    except (TypeError, ValueError):
        return {'place': None, 'reason': 'bad_coords'}

    cache_key = f'reverse:{lang}:{lat}:{lon}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = {
        'lat': lat,
        'lon': lon,
        'format': 'jsonv2',
        'zoom': 16,
        'accept-language': lang or 'fr',
    }
    try:
        resp = requests.get(
            f'{_base_url()}/reverse', params=params,
            headers=_headers(), timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json() or {}
        result = {
            'place': _simplify(data) if data.get('display_name') else None,
            'reason': '',
        }
    except requests.RequestException as exc:
        logger.warning('Reverse geocoding failed: %s', exc)
        result = {'place': None, 'reason': 'network'}
    except (ValueError, TypeError) as exc:
        logger.warning('Reverse geocoding returned invalid JSON: %s', exc)
        result = {'place': None, 'reason': 'network'}

    _cache_put(cache_key, result)
    return result


def static_map_url(lat, lon, zoom: int = 14) -> str:
    """Optional static preview (kept for fallbacks when Leaflet cannot load)."""
    if lat is None or lon is None:
        return ''
    return f'{_base_url()}/static?' + urlencode({
        'center': f'{lat},{lon}', 'zoom': zoom,
    })
