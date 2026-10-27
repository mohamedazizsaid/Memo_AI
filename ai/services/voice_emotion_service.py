"""
MemoAi — Voice Emotion Service
================================
Détecte les émotions exprimées dans la voix d'une note audio.

Ce module est un complément à la transcription textuelle.
Il NE constitue PAS une mesure certaine de l'état émotionnel :
l'estimation vocale est présentée comme une indication complémentaire,
avec une incertitude explicite affichée à l'utilisateur.

Modèle utilisé :
    Random Forest / SVM entraîné avec librosa sur RAVDESS + CREMA-D.
    Chemin : ai/ml/models/voice_emotion_rf.joblib

Pipeline d'inférence :
    audio_bytes / audio_path
        → librosa.load()
        → extract_features() → vecteur 364-dim
        → StandardScaler → RandomForest.predict_proba()
        → calibrate_voice_emotion()
        → dict résultat avec disclaimer

Classes produites (mappées sur EMOTION_META de emotion_service) :
    neutre, joie, tristesse, colere, peur, degout, surprise
"""

import io
import logging
import tempfile
from pathlib import Path

import numpy as np

logger = logging.getLogger('memoai')

# ── Chemin du modèle ───────────────────────────────────────────────────────────
BASE_ML_DIR        = Path(__file__).resolve().parent.parent / 'ml'
_MODEL_CANDIDATES  = [
    BASE_ML_DIR / 'models' / 'voice_emotion_rf.joblib',
    BASE_ML_DIR / 'models' / 'voice_emotion_svm.joblib',
    BASE_ML_DIR / 'models' / 'voice_emotion_mlp.joblib',
]

# ── Seuil de confiance minimale ────────────────────────────────────────────────
# En dessous de ce seuil la prédiction est retournée comme "incertaine"
CONFIDENCE_THRESHOLD = 0.35

# ── Cache modèle ────────────────────────────────────────────────────────────────
_VOICE_MODEL      = None
_VOICE_MODEL_NAME = None


def _load_voice_model():
    """Charge le premier modèle disponible parmi les candidats."""
    global _VOICE_MODEL, _VOICE_MODEL_NAME
    if _VOICE_MODEL is not None:
        return _VOICE_MODEL, _VOICE_MODEL_NAME

    for candidate in _MODEL_CANDIDATES:
        if candidate.exists():
            try:
                import joblib
                logger.info("Chargement du modèle voice emotion : %s", candidate)
                _VOICE_MODEL = joblib.load(candidate)
                _VOICE_MODEL_NAME = candidate.stem
                return _VOICE_MODEL, _VOICE_MODEL_NAME
            except Exception as exc:
                logger.warning("Echec chargement %s : %s", candidate, exc)

    logger.info(
        "Aucun modèle voice emotion disponible. "
        "Entraîner avec : python ai/ml/train_voice_emotion.py --demo"
    )
    return None, None


# ── Extraction de features (identique au script d'entraînement) ────────────────

def _extract_features(audio_data: bytes, mime_type: str = 'audio/wav') -> np.ndarray | None:
    """
    Extrait un vecteur de 364 features audio depuis des bytes bruts.

    Features :
        - 40 MFCC mean + std  → 80
        - 12 Chroma mean + std → 24
        - ZCR mean + std       → 2
        - RMS mean + std       → 2
        - 128 Mel mean + std   → 256
                                 ───
                                 364 dimensions
    """
    try:
        import librosa
    except ImportError:
        logger.error("librosa non installé. Lancer : pip install librosa soundfile")
        return None

    try:
        y, sr = librosa.load(io.BytesIO(audio_data), sr=22050, duration=3.0, mono=True)
    except Exception as exc:
        logger.warning("librosa.load échoué : %s", exc)
        # Fallback : écriture dans un fichier temporaire
        try:
            suffix = _mime_to_ext(mime_type)
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            y, sr = librosa.load(tmp_path, sr=22050, duration=3.0, mono=True)
            Path(tmp_path).unlink(missing_ok=True)
        except Exception as exc2:
            logger.warning("Fallback audio load échoué : %s", exc2)
            return None

    if len(y) < sr * 0.5:
        logger.debug("Audio trop court (<0.5s), ignoré")
        return None

    feats = []

    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
    feats.extend([np.mean(mfccs, axis=1), np.std(mfccs, axis=1)])

    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    feats.extend([np.mean(chroma, axis=1), np.std(chroma, axis=1)])

    zcr = librosa.feature.zero_crossing_rate(y)
    feats.append([np.mean(zcr), np.std(zcr)])

    rms = librosa.feature.rms(y=y)
    feats.append([np.mean(rms), np.std(rms)])

    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    feats.extend([np.mean(mel_db, axis=1), np.std(mel_db, axis=1)])

    return np.concatenate([np.atleast_1d(f) for f in feats]).astype(np.float32)


def _mime_to_ext(mime_type: str) -> str:
    return {
        'audio/wav':  '.wav',
        'audio/wave': '.wav',
        'audio/mpeg': '.mp3',
        'audio/mp3':  '.mp3',
        'audio/ogg':  '.ogg',
        'audio/webm': '.webm',
        'audio/mp4':  '.m4a',
        'audio/m4a':  '.m4a',
        'audio/flac': '.flac',
    }.get(mime_type.lower().split(';')[0].strip(), '.wav')


# ── Post-traitement et calibration ─────────────────────────────────────────────

def _calibrate_voice_result(proba_dict: dict, confidence: float) -> dict:
    """
    Applique quelques heuristiques pour atténuer les erreurs de classification
    fréquentes sur des modèles formés en anglais mais appliqués à des voix variées.

    Règles :
    1. Si confidence < CONFIDENCE_THRESHOLD → marquer comme "uncertain"
    2. Supprimer les classes avec proba < 2% (bruit de fond)
    3. Normaliser
    """
    filtered = {k: v for k, v in proba_dict.items() if v >= 0.02}
    total = sum(filtered.values()) or 1.0
    norm = {k: round(v / total, 3) for k, v in filtered.items()}

    best = max(norm, key=norm.get)
    best_score = norm[best]

    uncertain = confidence < CONFIDENCE_THRESHOLD

    return {
        'emotion': best,
        'score': round(float(best_score), 3),
        'probabilities': norm,
        'uncertain': uncertain,
        'confidence_threshold': CONFIDENCE_THRESHOLD,
    }


# ── Point d'entrée public ──────────────────────────────────────────────────────

def classify_voice_emotion(
    audio_bytes: bytes | None = None,
    audio_path: str | None = None,
    mime_type: str = 'audio/wav',
    lang: str = 'fr',
) -> dict:
    """
    Analyse les émotions vocales dans un fichier audio.

    Paramètres :
        audio_bytes : contenu binaire du fichier audio
        audio_path  : chemin alternatif si audio_bytes est None
        mime_type   : type MIME (audio/wav, audio/mpeg, etc.)
        lang        : langue pour les labels ('fr' ou 'en')

    Retourne un dict :
        {
            'voice_emotion'       : str    — classe prédite (ex: 'joie')
            'voice_emotion_score' : float  — probabilité 0..1
            'voice_probabilities' : dict   — toutes les probabilités
            'uncertain'           : bool   — True si confiance insuffisante
            'model_used'          : str    — nom du modèle chargé
            'disclaimer'          : str    — message d'avertissement
            'label'               : str    — label localisé
            'emoji'               : str    — icône SVG
            'color'               : str    — couleur hex
            'available'           : bool   — False si modèle absent
        }

    ⚠ IMPORTANT : cette estimation vocale est complémentaire à la transcription
    et NE constitue PAS une mesure certaine de l'état émotionnel de l'utilisateur.
    Les modèles sont entraînés sur des données principalement en anglais.
    """
    from ai.services.emotion_service import get_emotion_meta, EMOTION_META

    _DISCLAIMER = {
        'fr': (
            "Cette estimation vocale est indicative et non certaine. "
            "Les modèles audio sont entraînés principalement sur des données "
            "en anglais et peuvent être imprécis sur d'autres langues ou accents."
        ),
        'en': (
            "This vocal estimate is indicative, not definitive. "
            "Audio models are trained primarily on English data and may be "
            "inaccurate for other languages or accents."
        ),
    }

    def _unavailable(reason: str) -> dict:
        meta = get_emotion_meta('neutre', lang)
        return {
            'voice_emotion': None,
            'voice_emotion_score': None,
            'voice_probabilities': {},
            'uncertain': True,
            'model_used': 'unavailable',
            'disclaimer': _DISCLAIMER.get(lang, _DISCLAIMER['fr']),
            'label': meta['label'],
            'emoji': meta['emoji'],
            'color': meta['color'],
            'available': False,
            'reason': reason,
        }

    # ── Charger le modèle ──────────────────────────────────────────────────────
    model, model_name = _load_voice_model()
    if model is None:
        return _unavailable("Modèle voice emotion non entraîné.")

    # ── Charger les bytes audio si chemin fourni ───────────────────────────────
    if audio_bytes is None and audio_path:
        try:
            audio_bytes = Path(audio_path).read_bytes()
        except Exception as exc:
            logger.warning("Impossible de lire %s : %s", audio_path, exc)
            return _unavailable(f"Fichier audio illisible : {exc}")

    if not audio_bytes:
        return _unavailable("Aucune donnée audio fournie.")

    # ── Extraction de features ─────────────────────────────────────────────────
    features = _extract_features(audio_bytes, mime_type)
    if features is None:
        return _unavailable("Extraction des features audio échouée (audio trop court ou format non supporté).")

    # ── Prédiction ─────────────────────────────────────────────────────────────
    try:
        proba_vec = model.predict_proba([features])[0]
        classes   = list(model.classes_)
        proba_dict = {classes[i]: float(proba_vec[i]) for i in range(len(classes))}
    except Exception as exc:
        logger.error("Erreur prédiction voice emotion : %s", exc)
        return _unavailable(f"Erreur de prédiction : {exc}")

    confidence = float(np.max(proba_vec))
    calibrated = _calibrate_voice_result(proba_dict, confidence)

    best_emo   = calibrated['emotion']
    best_score = calibrated['score']
    uncertain  = calibrated['uncertain']

    meta = get_emotion_meta(best_emo, lang)

    logger.info(
        "Voice emotion: %s (score=%.2f, uncertain=%s, model=%s)",
        best_emo, best_score, uncertain, model_name
    )

    return {
        'voice_emotion':       best_emo,
        'voice_emotion_score': best_score,
        'voice_probabilities': calibrated['probabilities'],
        'uncertain':           uncertain,
        'model_used':          model_name or 'voice_rf',
        'disclaimer':          _DISCLAIMER.get(lang, _DISCLAIMER['fr']),
        'label':               meta['label'],
        'emoji':               meta['emoji'],
        'color':               meta['color'],
        'available':           True,
    }
