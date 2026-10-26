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


MOOD_PRIORS = {
    'amazing':  {'joie': 5.0, 'surprise': 1.8, 'neutre': 0.6, 'tristesse': 0.05, 'degout': 0.02, 'peur': 0.05, 'colere': 0.02},
    'good':     {'joie': 3.5, 'neutre': 1.2, 'surprise': 1.0, 'tristesse': 0.1,  'degout': 0.05, 'peur': 0.1,  'colere': 0.05},
    'excited':  {'joie': 4.0, 'surprise': 2.5, 'neutre': 0.5, 'tristesse': 0.05, 'degout': 0.02, 'peur': 0.1,  'colere': 0.05},
    'grateful': {'joie': 4.5, 'neutre': 0.8, 'surprise': 0.8, 'tristesse': 0.1,  'degout': 0.02, 'peur': 0.05, 'colere': 0.02},
    'neutral':  {'neutre': 3.5, 'joie': 1.0, 'tristesse': 0.8, 'surprise': 0.8, 'peur': 0.6,  'colere': 0.5, 'degout': 0.3},
    'tired':    {'neutre': 3.0, 'tristesse': 1.4, 'peur': 1.0, 'joie': 0.5, 'colere': 0.5,  'degout': 0.3, 'surprise': 0.3},
    'stressed': {'peur': 4.5, 'colere': 2.0, 'tristesse': 0.6, 'neutre': 0.8, 'degout': 0.4,  'joie': 0.05, 'surprise': 0.5},
    'sad':      {'tristesse': 5.0, 'peur': 1.2, 'colere': 0.8, 'neutre': 0.5, 'degout': 0.4,  'joie': 0.02, 'surprise': 0.2},
    'angry':    {'colere': 5.0, 'degout': 2.0, 'tristesse': 0.8, 'peur': 0.8, 'neutre': 0.4,  'joie': 0.02, 'surprise': 0.3},
}

DISGUST_KEYWORDS = ['degout', 'dégoût', 'vomir', 'nausée', 'nausee', 'immonde', 'infect', 'ecoeurant', 'écœurant', 'repugne', 'répugne', 'avarié', 'avarie', 'fétide', 'fetide']
JOY_KEYWORDS = ['bonheur', 'plaisir', 'joie', 'rires', 'rire', 'sourire', 'merveilleux', 'magique', 'sublime', 'incroyable', 'incroyables', 'creativite', 'créativité', 'chaleur tranquille', 'amis', 'amitié', 'amities', 'amour', 'doux', 'douces', 'parfait']


def _calibrate_with_context(raw_probs: dict, text: str, user_mood: str = None) -> tuple[str, float, dict]:
    """
    Combines raw ML probabilities with declared user mood prior and contextual safeguards
    to ensure logical, robust emotion estimation for personal diaries.
    """
    probs = dict(raw_probs)
    t_lower = text.lower()

    # 1. Disgust safeguard: do not trigger disgust unless explicit revulsion exists
    has_disgust_kw = any(w in t_lower for w in DISGUST_KEYWORDS)
    if not has_disgust_kw and 'degout' in probs:
        probs['degout'] = probs['degout'] * 0.1

    # 2. Joy reinforcement: boost joie if positive reflective diary vocabulary is present
    has_joy_kw = any(w in t_lower for w in JOY_KEYWORDS)
    if has_joy_kw and 'joie' in probs:
        probs['joie'] = probs['joie'] * 1.8
        if 'tristesse' in probs and not any(w in t_lower for w in ['mort', 'deuil', 'pleure', 'pleuré', 'larmes', 'dévasté']):
            probs['tristesse'] = probs['tristesse'] * 0.3

    # 3. Bayesian prior from user's declared mood
    mood_key = (user_mood or '').strip().lower()
    priors = MOOD_PRIORS.get(mood_key)
    if priors:
        for emo in probs:
            probs[emo] = probs[emo] * priors.get(emo, 1.0)

    # Re-normalize probabilities
    total = sum(probs.values()) or 1.0
    norm_probs = {k: round(v / total, 3) for k, v in probs.items()}

    best_emo = max(norm_probs, key=norm_probs.get)
    best_score = norm_probs[best_emo]

    return best_emo, round(float(best_score), 2), norm_probs


def classify_emotion(text: str, lang: str = 'fr', user_mood: str = None) -> dict:
    """
    Main entry point: classifies a French text into one of the 7 emotions.
    Optionally incorporates user_mood prior to align with declared feelings.
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
            outputs = model(cleaned[:512])[0]
            raw_probs = {str(item['label']).lower(): float(item['score']) for item in outputs}
            best_emo, score, final_probs = _calibrate_with_context(raw_probs, cleaned, user_mood)
            meta = get_emotion_meta(best_emo, lang)
            return {
                'emotion': best_emo,
                'score': score,
                'label': meta['label'],
                'emoji': meta['emoji'],
                'color': meta['color'],
                'description': meta['description'],
                'probabilities': final_probs,
                'model_used': 'camembert',
            }
        except Exception as exc:
            logger.warning("CamemBERT prediction failed: %s, falling back to SVM", exc)

    if model_type == 'svm' and model is not None:
        try:
            probs_list = model.predict_proba([cleaned])[0]
            classes = list(model.classes_)
            raw_probs = {classes[i]: float(probs_list[i]) for i in range(len(classes))}
            best_emo, score, final_probs = _calibrate_with_context(raw_probs, cleaned, user_mood)
            meta = get_emotion_meta(best_emo, lang)
            return {
                'emotion': best_emo,
                'score': score,
                'label': meta['label'],
                'emoji': meta['emoji'],
                'color': meta['color'],
                'description': meta['description'],
                'probabilities': final_probs,
                'model_used': 'svm',
            }
        except Exception as exc:
            logger.warning("SVM prediction failed: %s, falling back to lexicon", exc)

    lex_res = _lexical_fallback(cleaned)
    best_emo, score, final_probs = _calibrate_with_context(lex_res['probabilities'], cleaned, user_mood)
    meta = get_emotion_meta(best_emo, lang)
    return {
        'emotion': best_emo,
        'score': score,
        'label': meta['label'],
        'emoji': meta['emoji'],
        'color': meta['color'],
        'description': meta['description'],
        'probabilities': final_probs,
        'model_used': 'lexical_fallback',
    }

