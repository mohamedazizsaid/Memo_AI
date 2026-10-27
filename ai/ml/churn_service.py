"""
MemoAi — Churn Prediction Service
=================================
Service applicatif pour évaluer le risque de départ d'un utilisateur.
Utilise le modèle entraîné (Random Forest) sérialisé dans models/churn_model.joblib.

Fournit :
- predict_user(user) : Analyse détaillée d'un utilisateur individuel
- predict_users(user_queryset) : Analyse par lot pour le scan périodique
"""

import logging
from pathlib import Path
import joblib
import numpy as np

from ai.ml.churn_features import FEATURE_NAMES, extract_user_features, features_to_vector

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parent / "models" / "churn_model.joblib"


class ChurnPredictor:
    """Singleton chargeant le modèle et effectuant les inférences de churn."""

    _instance = None
    _model_data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChurnPredictor, cls).__new__(cls)
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        """Charge le modèle sérialisé ou entraîne un modèle initial si absent."""
        if not MODEL_PATH.exists():
            logger.warning(f"[ChurnPredictor] Modele introuvable a {MODEL_PATH}. Lancement de l'entrainement...")
            from ai.ml.train_churn_model import train_model
            self._model_data = train_model(output_path=MODEL_PATH)
        else:
            try:
                self._model_data = joblib.load(MODEL_PATH)
                logger.info(f"[ChurnPredictor] Modele charge avec succes ({self._model_data.get('model_type')}).")
            except Exception as e:
                logger.error(f"[ChurnPredictor] Erreur chargement modele : {e}. Re-entrainement...")
                from ai.ml.train_churn_model import train_model
                self._model_data = train_model(output_path=MODEL_PATH)

    @property
    def pipeline(self):
        return self._model_data["pipeline"]

    @property
    def metrics(self):
        return self._model_data.get("metrics", {})

    @property
    def feature_importances(self):
        return self._model_data.get("feature_importances", {})

    def predict_features(self, features_dict):
        """
        Prédit le risque à partir d'un dictionnaire de features.
        Retourne :
            {
                'is_churn': bool,
                'churn_probability': float,
                'risk_level': 'low' | 'medium' | 'high',
                'reasons': list[str],
            }
        """
        vec = np.array([features_to_vector(features_dict)], dtype=np.float32)
        proba = float(self.pipeline.predict_proba(vec)[0, 1])
        is_churn = bool(proba >= 0.50)

        if proba >= 0.70:
            risk_level = "high"
        elif proba >= 0.45:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Diagnostic explicatif pour l'email / notification
        reasons = []
        days_entry = features_dict.get("days_since_last_entry", 0)
        days_login = features_dict.get("days_since_last_login", 0)
        drop_ratio = features_dict.get("activity_drop_ratio", 0)
        entries_7d = features_dict.get("entries_last_7d", 0)

        if days_entry >= 14:
            reasons.append(f"Aucune note écrite depuis {int(days_entry)} jours")
        elif days_entry >= 7:
            reasons.append(f"Dernière note rédigée il y a {int(days_entry)} jours")

        if days_login >= 10:
            reasons.append(f"Absence de connexion depuis {int(days_login)} jours")

        if drop_ratio >= 0.60:
            reasons.append(f"Baisse d'activité de {int(drop_ratio * 100)}% sur le dernier mois")

        if entries_7d == 0:
            reasons.append("Aucune activité sur les 7 derniers jours")

        return {
            "is_churn": is_churn,
            "churn_probability": round(proba, 3),
            "risk_level": risk_level,
            "reasons": reasons,
            "features": features_dict,
        }

    def predict_user(self, user):
        """Évalue un utilisateur Django et retourne son profil de churn."""
        features = extract_user_features(user)
        res = self.predict_features(features)
        res["user_id"] = str(user.id)
        res["user_email"] = user.email
        return res

    def predict_users_batch(self, users):
        """Évalue une liste d'utilisateurs en une seule passe."""
        results = []
        for user in users:
            try:
                results.append(self.predict_user(user))
            except Exception as e:
                logger.error(f"[ChurnPredictor] Erreur sur user {user.id}: {e}")
        return results


def get_churn_predictor():
    """Factory helper pour obtenir l'instance unique."""
    return ChurnPredictor()
