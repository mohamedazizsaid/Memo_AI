"""
MemoAi — Emotion Classification Service
Classifies journal entries into 7 core French emotions:
- joie (joy)
- tristesse (sadness)
- colere (anger)
- peur (fear)
- surprise (surprise)
- degout (disgust)
- neutre (neutral)

Uses fine-tuned CamemBERT when available, otherwise the calibrated TF-IDF + SVM baseline,
with a robust lexical fallback if models are not present.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger('memoai')

BASE_ML_DIR = Path(__file__).resolve().parent.parent / 'ml'
SVM_MODEL_PATH = BASE_ML_DIR / 'models' / 'emotion_svm.joblib'
CAMEMBERT_DIR = BASE_ML_DIR / 'models' / 'camembert_emotion'

EMOTION_META = {
    'joie': {
        'fr': 'Joie',
        'en': 'Joy',
        'emoji': '😊',
        'color': '#10b981',
        'description': "Sentiment de plaisir, de bonheur et d'accomplissement.",
    },
    'tristesse': {
        'fr': 'Tristesse',
        'en': 'Sadness',
        'emoji': '😢',
        'color': '#64748b',
        'description': "Sentiment de mélancolie, de perte ou de peine.",
    },
    'colere': {
        'fr': 'Colère',
        'en': 'Anger',
        'emoji': '😠',
        'color': '#ef4444',
        'description': "Sentiment d'irritation, d'exaspération ou de révolte.",
    },
    'peur': {
        'fr': 'Peur',
        'en': 'Fear',
        'emoji': '😨',
        'color': '#8b5cf6',
        'description': "Sentiment d'inquiétude, d'anxiété ou d'appréhension.",
    },
    'surprise': {
        'fr': 'Surprise',
        'en': 'Surprise',
        'emoji': '😲',
        'color': '#f59e0b',
        'description': "Étonnement devant un fait inattendu ou inhabituel.",
    },
    'degout': {
        'fr': 'Dégoût',
        'en': 'Disgust',
        'emoji': '🤢',
        'color': '#0d9488',
        'description': "Aversion ou rejet profond envers une situation.",
    },
    'neutre': {
        'fr': 'Neutre',
        'en': 'Neutral',
        'emoji': '😐',
        'color': '#94a3b8',
        'description': "Tonalité posée, descriptive sans charge émotionnelle marquée.",
    },
}

_LOADED_MODEL = None
_MODEL_TYPE = None


def get_emotion_meta(emotion_key: str, lang: str = 'fr') -> dict:
    key = str(emotion_key or 'neutre').strip().lower()
    meta = EMOTION_META.get(key, EMOTION_META['neutre'])
    return {
        'key': key,
        'label': meta.get(lang, meta['fr']),
        'emoji': meta.get('emoji', '😐'),
        'color': meta.get('color', '#94a3b8'),
        'description': meta.get('description', ''),
    }


def _load_model():
    global _LOADED_MODEL, _MODEL_TYPE
    if _LOADED_MODEL is not None:
        return _LOADED_MODEL, _MODEL_TYPE

    # 1. Try CamemBERT if exported
    if CAMEMBERT_DIR.exists() and (CAMEMBERT_DIR / 'config.json').exists():
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
            logger.info("Loading fine-tuned CamemBERT emotion model from %s", CAMEMBERT_DIR)
            tokenizer = AutoTokenizer.from_pretrained(str(CAMEMBERT_DIR))
            model = AutoModelForSequenceClassification.from_pretrained(str(CAMEMBERT_DIR))
            clf = pipeline("text-classification", model=model, tokenizer=tokenizer, return_all_scores=True)
            _LOADED_MODEL = clf
            _MODEL_TYPE = 'camembert'
            return _LOADED_MODEL, _MODEL_TYPE
        except Exception as exc:
            logger.warning("Could not load CamemBERT model (%s), trying SVM baseline", exc)

    # 2. Try TF-IDF + SVM baseline
    if SVM_MODEL_PATH.exists():
        try:
            import joblib
            logger.info("Loading trained TF-IDF + SVM emotion model from %s", SVM_MODEL_PATH)
            pipeline_obj = joblib.load(SVM_MODEL_PATH)
            _LOADED_MODEL = pipeline_obj
            _MODEL_TYPE = 'svm'
            return _LOADED_MODEL, _MODEL_TYPE
        except Exception as exc:
            logger.warning("Could not load SVM emotion model (%s)", exc)

    _LOADED_MODEL = None
    _MODEL_TYPE = 'fallback'
    return _LOADED_MODEL, _MODEL_TYPE


def _lexical_fallback(text: str) -> dict:
    """Keyword-based fallback if ML model is unavailable."""
    text_lower = text.lower()
    keywords = {
        'joie': ['heureux', 'heureuse', 'joie', 'magnifique', 'merveilleux', 'content', 'contente', 'super', 'génial', 'fête', 'amour', 'adore', 'rires', 'sourire'],
        'tristesse': ['triste', 'chagrin', 'pleure', 'pleuré', 'larmes', 'seul', 'seule', 'dévasté', 'manque', 'deuil', 'solitude', 'abattu'],
        'colere': ['colère', 'énervé', 'fâché', 'inadmissible', 'honteux', 'rage', 'déteste', 'insupportable', 'furieux', 'furieuse'],
        'peur': ['peur', 'angoisse', 'panique', 'effrayé', 'terreur', 'crainte', 'inquiet', 'inquiète', 'tremble', 'menace'],
        'surprise': ['surprise', 'surpris', 'étonné', 'inattendu', 'incroyable', 'stupéfait', 'choc', 'wahou', 'bizarre'],
        'degout': ['dégoût', 'écoeurant', 'infecte', 'répugne', 'beurk', 'nausée', 'immonde', 'horrible'],
    }

    scores = {emo: 0 for emo in EMOTION_META}
    scores['neutre'] = 1  # Base score

    for emo, words in keywords.items():
        for w in words:
            if w in text_lower:
                scores[emo] += 2

    best_emo = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    score = min(0.95, scores[best_emo] / total if best_emo != 'neutre' else 0.6)

    meta = get_emotion_meta(best_emo)
    return {
        'emotion': best_emo,
        'score': round(float(score), 2),
        'label': meta['label'],
        'emoji': meta['emoji'],
        'color': meta['color'],
        'description': meta['description'],
        'probabilities': {k: round(v / total, 3) for k, v in scores.items()},
        'model_used': 'lexical_fallback',
    }


def classify_emotion(text: str, lang: str = 'fr') -> dict:
    """
    Main entry point: classifies a French text into one of the 7 emotions.
    Returns:
        dict: {emotion, score, label, emoji, color, description, probabilities, model_used}
    """
    cleaned = (text or '').strip()
    if not cleaned or len(cleaned) < 5:
        meta = get_emotion_meta('neutre', lang)
        return {
            'emotion': 'neutre',
            'score': 0.5,
            'label': meta['label'],
            'emoji': meta['emoji'],
            'color': meta['color'],
            'description': meta['description'],
            'probabilities': {'neutre': 1.0},
            'model_used': 'default',
        }

    model, model_type = _load_model()

    if model_type == 'camembert' and model is not None:
        try:
            # Hugging Face text-classification pipeline
            outputs = model(cleaned[:512])[0]
            # outputs is a list of {'label': 'joie', 'score': 0.85}
            best = max(outputs, key=lambda x: x['score'])
            emo_key = str(best['label']).lower()
            probs = {str(item['label']).lower(): round(float(item['score']), 3) for item in outputs}
            meta = get_emotion_meta(emo_key, lang)
            return {
                'emotion': emo_key,
                'score': round(float(best['score']), 2),
                'label': meta['label'],
                'emoji': meta['emoji'],
                'color': meta['color'],
                'description': meta['description'],
                'probabilities': probs,
                'model_used': 'camembert',
            }
        except Exception as exc:
            logger.warning("CamemBERT prediction failed: %s, falling back to SVM", exc)

    if model_type == 'svm' and model is not None:
        try:
            pred = model.predict([cleaned])[0]
            probs_list = model.predict_proba([cleaned])[0]
            classes = list(model.classes_)
            probs = {classes[i]: round(float(probs_list[i]), 3) for i in range(len(classes))}
            score = float(max(probs_list))
            meta = get_emotion_meta(pred, lang)
            return {
                'emotion': str(pred).lower(),
                'score': round(score, 2),
                'label': meta['label'],
                'emoji': meta['emoji'],
                'color': meta['color'],
                'description': meta['description'],
                'probabilities': probs,
                'model_used': 'svm',
            }
        except Exception as exc:
            logger.warning("SVM prediction failed: %s, falling back to lexicon", exc)

    return _lexical_fallback(cleaned)
