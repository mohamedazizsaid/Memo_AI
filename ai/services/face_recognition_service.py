"""
MemoAi — Face Recognition Service
Local face detection, embedding, and matching using face_recognition (dlib).
All biometric processing stays local — no data sent to external services.

Privacy by design:
- Embeddings stored as numpy arrays in DB (encrypted in production)
- User consent required before processing
- Full deletion support
"""

import logging
import io
import numpy as np
from typing import Optional
from django.conf import settings

logger = logging.getLogger('memoai')

# Lazy import to avoid startup crash if not installed
_face_recognition = None
_PIL = None


def _get_face_recognition():
    global _face_recognition
    if _face_recognition is None:
        try:
            import face_recognition as fr
            _face_recognition = fr
        except ImportError:
            logger.warning(
                "face_recognition library not installed. "
                "Install with: pip install face-recognition"
            )
    return _face_recognition


def is_available():
    """Check if face recognition is available and enabled."""
    return (
        settings.FACE_RECOGNITION_ENABLED
        and _get_face_recognition() is not None
        and not settings.AI_MOCK_MODE
    )


def detect_faces(image_bytes: bytes) -> list:
    """
    Detect faces in an image.
    
    Args:
        image_bytes: Raw image bytes (JPEG/PNG)
        
    Returns:
        list of dicts: [{
            'bounding_box': {'top': int, 'right': int, 'bottom': int, 'left': int},
            'embedding': list[float] (128-dim),
            'confidence': float
        }]
    """
    if not is_available():
        if settings.AI_MOCK_MODE:
            return []  # Mock: no faces detected
        return []

    fr = _get_face_recognition()
    if not fr:
        return []

    try:
        import PIL.Image

        # Convert bytes to numpy array
        image = PIL.Image.open(io.BytesIO(image_bytes))
        image = image.convert('RGB')
        image_array = np.array(image)

        # Detect face locations (using HOG model — faster; use 'cnn' for better accuracy)
        face_locations = fr.face_locations(image_array, model='hog')

        if not face_locations:
            return []

        # Generate face encodings (128-dim embeddings)
        face_encodings = fr.face_encodings(image_array, face_locations)

        results = []
        for location, encoding in zip(face_locations, face_encodings):
            top, right, bottom, left = location
            results.append({
                'bounding_box': {
                    'top': top,
                    'right': right,
                    'bottom': bottom,
                    'left': left,
                },
                'embedding': encoding.tolist(),  # Convert numpy to list for JSON serialization
                'confidence': 1.0,  # HOG model doesn't provide confidence; CNN does
            })

        logger.info(f"Detected {len(results)} face(s)")
        return results

    except Exception as e:
        logger.error(f"Face detection error: {e}", exc_info=True)
        return []


def compute_embedding(image_bytes: bytes) -> Optional[list]:
    """
    Compute face embedding from a single-face image (e.g., a cropped face).
    
    Returns:
        list[float]: 128-dimensional embedding, or None if no face found
    """
    faces = detect_faces(image_bytes)
    if faces:
        return faces[0]['embedding']
    return None


def compare_embeddings(
    embedding1: list,
    embedding2: list,
    threshold: float = None
) -> tuple:
    """
    Compare two face embeddings.
    
    Args:
        embedding1: First face embedding (list of 128 floats)
        embedding2: Second face embedding
        threshold: Match threshold (default from settings)
        
    Returns:
        (is_match: bool, distance: float)
    """
    if threshold is None:
        threshold = settings.FACE_RECOGNITION_CONFIDENCE_THRESHOLD

    try:
        enc1 = np.array(embedding1)
        enc2 = np.array(embedding2)

        # Euclidean distance between embeddings
        distance = np.linalg.norm(enc1 - enc2)
        is_match = distance <= threshold

        return bool(is_match), float(distance)

    except Exception as e:
        logger.error(f"Embedding comparison error: {e}")
        return False, 1.0


def find_matching_person(embedding: list, known_persons: list) -> Optional[dict]:
    """
    Find the closest matching person from a list of known persons.
    
    Args:
        embedding: New face embedding to match
        known_persons: List of dicts with 'id', 'name', 'embedding'
        
    Returns:
        dict: Best matching person with 'id', 'name', 'distance', or None
    """
    if not known_persons or not embedding:
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
                'name': person['name'],
                'distance': distance,
                'confidence': max(0, 1 - (distance / threshold)),
            }

    return best_match


def embedding_to_db(embedding: list) -> str:
    """Convert embedding list to a string for database storage."""
    return ','.join(map(str, embedding))


def db_to_embedding(db_string: str) -> list:
    """Convert database string back to embedding list."""
    if not db_string:
        return []
    return [float(x) for x in db_string.split(',')]
