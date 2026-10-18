"""
MemoAi — Face service.

Primary detection/recognition happens **client-side with face-api.js**: the
browser computes 128-d face descriptors that we store on ``Person`` and match
against journal photos. This module provides the server-side utilities:

* ``detect_faces``    — OpenCV Haar fallback that yields bounding boxes even
                        when the browser/JS is unavailable (no identity).
* ``compute_embedding`` / ``compare_embeddings`` / ``find_matching_person``
                      — euclidean matching over any equal-length descriptors
                        (face-api.js descriptors are 128-d, like dlib's).

All biometric processing stays local. numpy/OpenCV are imported lazily so the
app still boots when they are absent.
"""

import io
import logging

from django.conf import settings

logger = logging.getLogger('memoai')

_np = None
_cv2 = None
_cascade = None
_cascade_loaded = False


def _get_numpy():
    global _np
    if _np is None:
        try:
            import numpy as np
            _np = np
        except ImportError:
            logger.warning("numpy not installed — face matching disabled.")
    return _np


def _get_cv2():
    global _cv2
    if _cv2 is None:
        try:
            import cv2
            _cv2 = cv2
        except ImportError:
            logger.warning("opencv not installed — server-side face detection disabled.")
    return _cv2


def _get_cascade():
    global _cascade, _cascade_loaded
    if _cascade_loaded:
        return _cascade
    _cascade_loaded = True
    cv2 = _get_cv2()
    if cv2 is None:
        return None
    try:
        path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        _cascade = cv2.CascadeClassifier(path)
        if _cascade.empty():
            _cascade = None
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not load Haar cascade: %s", exc)
        _cascade = None
    return _cascade


def is_available() -> bool:
    """Server-side detection is available when OpenCV + numpy are installed."""
    return bool(settings.FACE_RECOGNITION_ENABLED) and _get_cv2() is not None and _get_numpy() is not None


def detect_faces(image_bytes: bytes) -> list:
    """
    Detect faces with OpenCV. Returns a list of
    ``{'bounding_box': {...}, 'embedding': None, 'confidence': float}``.
    Identity (embedding) comes from the client-side face-api.js descriptors.
    """
    if not is_available() or not image_bytes:
        return []

    cv2 = _get_cv2()
    np = _get_numpy()
    cascade = _get_cascade()
    if cascade is None:
        return []

    try:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return []
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(36, 36))

        results = []
        for (x, y, w, h) in faces:
            results.append({
                'bounding_box': {
                    'left': int(x), 'top': int(y),
                    'right': int(x + w), 'bottom': int(y + h),
                    'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h),
                },
                'embedding': None,
                'confidence': 0.85,
            })
        logger.info("OpenCV detected %d face(s)", len(results))
        return results
    except Exception as exc:
        logger.error("Face detection error: %s", exc, exc_info=True)
        return []


def compute_embedding(image_bytes: bytes):
    """Convenience wrapper returning the first available descriptor (or None)."""
    faces = detect_faces(image_bytes)
    for face in faces:
        if face.get('embedding'):
            return face['embedding']
    return None


def compare_embeddings(embedding1, embedding2, threshold: float = None):
    """Euclidean distance between two descriptors → (is_match, distance)."""
    np = _get_numpy()
    if np is None:
        return False, 1.0
    if threshold is None:
        threshold = settings.FACE_RECOGNITION_CONFIDENCE_THRESHOLD
    try:
        a = np.asarray(embedding1, dtype=float)
        b = np.asarray(embedding2, dtype=float)
        if a.shape != b.shape or a.size == 0:
            return False, 1.0
        distance = float(np.linalg.norm(a - b))
        return bool(distance <= threshold), distance
    except Exception as exc:
        logger.error("Embedding comparison error: %s", exc)
        return False, 1.0


def find_matching_person(embedding, known_persons: list):
    """
    Return the closest known person for ``embedding`` or ``None``.
    ``known_persons``: list of dicts with 'id', 'name' and 'embedding'.
    """
    if not embedding or not known_persons:
        return None

    best_match = None
    best_distance = float('inf')
    threshold = settings.FACE_RECOGNITION_CONFIDENCE_THRESHOLD

    for person in known_persons:
        person_embedding = person.get('embedding')
        if not person_embedding:
            continue
        is_match, distance = compare_embeddings(embedding, person_embedding, threshold)
        if is_match and distance < best_distance:
            best_distance = distance
            best_match = {
                'id': person['id'],
                'name': person.get('name', ''),
                'distance': distance,
                'confidence': max(0.0, 1.0 - (distance / threshold)) if threshold else 0.0,
            }
    return best_match


def embedding_to_db(embedding) -> str:
    """Serialise a descriptor list into a comma-separated string."""
    if not embedding:
        return ''
    return ','.join(f"{float(x):.6f}" for x in embedding)


def db_to_embedding(db_string) -> list:
    """Parse a comma-separated descriptor string back into a float list."""
    if not db_string:
        return []
    try:
        return [float(x) for x in str(db_string).split(',') if x != '']
    except (TypeError, ValueError):
        return []
