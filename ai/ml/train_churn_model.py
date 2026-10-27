"""
MemoAi — Churn Model Training
=============================
Entraîne un classifieur Random Forest pour prédire le risque d'abandon (churn)
des utilisateurs à partir de leurs signaux d'interaction avec la plateforme MemoAi.

Caractéristiques :
- Pipeline standardisé (StandardScaler + RandomForestClassifier)
- Pondération équilibrée des classes (class_weight='balanced')
- Métriques complètes : Accuracy, Precision, Recall, F1-score, ROC-AUC
- Extraction des importances des variables (feature importances)
- Sérialisation avec Joblib dans ai/ml/models/churn_model.joblib

Usage :
    python ai/ml/train_churn_model.py [--dataset ai/ml/data/churn_dataset.csv]
"""

import os
import sys
import csv
import logging
from pathlib import Path
from datetime import datetime

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix,
)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DATASET_PATH = DATA_DIR / "churn_dataset.csv"
MODEL_OUTPUT_PATH = MODELS_DIR / "churn_model.joblib"

# Importer les noms des variables
sys.path.insert(0, str(BASE_DIR.parent.parent))
from ai.ml.churn_features import FEATURE_NAMES


def load_dataset(csv_path):
    """Charge le fichier CSV en matrices X et y NumPy."""
    if not csv_path.exists():
        logger.info(f"Dataset introuvable a {csv_path}. Generation automatique...")
        from ai.ml.generate_churn_dataset import generate_dataset
        generate_dataset(total_samples=3000, output_path=csv_path)

    X_list = []
    y_list = []

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vector = [float(row[name]) for name in FEATURE_NAMES]
            label = int(row["is_churn"])
            X_list.append(vector)
            y_list.append(label)

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int32)


def train_model(dataset_path=DEFAULT_DATASET_PATH, output_path=MODEL_OUTPUT_PATH):
    """Entraîne et évalue le modèle de prédiction du churn."""
    dataset_path = Path(dataset_path)
    output_path = Path(output_path)

    logger.info(f"Chargement des donnees depuis {dataset_path}...")
    X, y = load_dataset(dataset_path)
    logger.info(f"Dataset charge : {X.shape[0]} exemples, {X.shape[1]} features.")

    # Split Train / Test stratifié
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    logger.info(f"Distribution Train : {np.bincount(y_train)} | Test : {np.bincount(y_test)}")

    # Construction du pipeline
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", RandomForestClassifier(
            n_estimators=150,
            max_depth=10,
            min_samples_split=4,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])

    logger.info("Entrainement du modele Random Forest...")
    pipeline.fit(X_train, y_train)

    # Prédictions sur le test set
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    # Calcul des métriques
    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred))
    rec = float(recall_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred))
    roc_auc = float(roc_auc_score(y_test, y_proba))

    print("\n" + "=" * 60)
    print(" === RESULTATS DU MODELE DE CHURN (MemoAI) ===")
    print("=" * 60)
    print(f"  * Accuracy  : {acc * 100:.2f}%")
    print(f"  * Precision : {prec * 100:.2f}%")
    print(f"  * Recall    : {rec * 100:.2f}%")
    print(f"  * F1-Score  : {f1 * 100:.2f}%")
    print(f"  * ROC-AUC   : {roc_auc * 100:.2f}%")
    print("\nMatrice de confusion :")
    cm = confusion_matrix(y_test, y_pred)
    print(f"  [VN: {cm[0, 0]:4d} | FP: {cm[0, 1]:4d}]")
    print(f"  [FN: {cm[1, 0]:4d} | VP: {cm[1, 1]:4d}]")
    print("\nRapport detaille :")
    print(classification_report(y_test, y_pred, target_names=["Actif (0)", "Churn (1)"]))

    # Importances des variables
    rf = pipeline.named_steps["classifier"]
    importances = rf.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]

    print("\nImportance des features (Top 8 facteurs d'interaction) :")
    feature_importance_dict = {}
    for rank, idx in enumerate(sorted_idx, 1):
        name = FEATURE_NAMES[idx]
        imp = float(importances[idx])
        feature_importance_dict[name] = round(imp, 4)
        if rank <= 8:
            print(f"  {rank}. {name:<25} : {imp * 100:5.2f}%")
    print("=" * 60 + "\n")

    # Sauvegarde du modèle
    payload = {
        "pipeline": pipeline,
        "feature_names": FEATURE_NAMES,
        "metrics": {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "roc_auc": roc_auc,
        },
        "feature_importances": feature_importance_dict,
        "trained_at": datetime.utcnow().isoformat(),
        "model_type": "RandomForestClassifier",
    }

    joblib.dump(payload, output_path)
    logger.info(f"Modele sauvegarde avec succes dans : {output_path}")
    return payload


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Entraine le modele de churn MemoAi")
    parser.add_argument("--dataset", type=str, default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--output", type=str, default=str(MODEL_OUTPUT_PATH))
    args = parser.parse_args()

    train_model(dataset_path=args.dataset, output_path=args.output)
