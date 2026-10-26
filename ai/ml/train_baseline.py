"""
MemoAi — Emotion Classifier Baseline Training
Trains a TF-IDF + LinearSVC (calibrated) model on the French-emotion dataset (JusteLeo/French-emotion).
Classes: joie, tristesse, colere, peur, surprise, degout, neutre.
"""

import os
import io
import csv
import logging
import requests
from pathlib import Path
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

HF_DATASET_BASE = "https://huggingface.co/datasets/JusteLeo/French-emotion/raw/main"
DATA_DIR = Path(__file__).resolve().parent / "data"
MODELS_DIR = Path(__file__).resolve().parent / "models"

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_OUTPUT_PATH = MODELS_DIR / "emotion_svm.joblib"

EMOTION_CLASSES = ["colere", "degout", "joie", "neutre", "peur", "surprise", "tristesse"]


def download_file(split_name: str) -> Path:
    """Download a CSV split from Hugging Face if not cached."""
    file_path = DATA_DIR / f"{split_name}.csv"
    if file_path.exists() and file_path.stat().st_size > 1000:
        logger.info("Using cached %s dataset: %s", split_name, file_path)
        return file_path

    url = f"{HF_DATASET_BASE}/{split_name}.csv"
    logger.info("Downloading %s from Hugging Face: %s", split_name, url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    with open(file_path, "wb") as f:
        f.write(resp.content)
    logger.info("Saved %s (%d bytes)", split_name, file_path.stat().st_size)
    return file_path


def load_dataset(file_path: Path):
    """Load texts and labels from CSV."""
    texts = []
    labels = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or "").strip()
            label = (row.get("label") or "").strip().lower()
            if text and label in EMOTION_CLASSES:
                texts.append(text)
                labels.append(label)
    return texts, labels


def train_baseline():
    """Download dataset, train TF-IDF + Calibrated LinearSVC, evaluate and save model."""
    train_path = download_file("train")
    val_path = download_file("validation")
    test_path = download_file("test")

    logger.info("Loading splits...")
    X_train, y_train = load_dataset(train_path)
    X_val, y_val = load_dataset(val_path)
    X_test, y_test = load_dataset(test_path)

    # Combine train + validation for maximal training signal
    X_full_train = X_train + X_val
    y_full_train = y_train + y_val

    logger.info("Training size: %d samples | Test size: %d samples", len(X_full_train), len(X_test))

    # Pipeline: TF-IDF n-grams (1, 2) + LinearSVC wrapped in CalibratedClassifierCV for confidence probabilities
    logger.info("Building TF-IDF + LinearSVC Pipeline...")
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=30000,
        sublinear_tf=True,
        strip_accents="unicode",
        min_df=2,
    )
    base_svc = LinearSVC(C=1.0, max_iter=2000, random_state=42)
    calibrated_svc = CalibratedClassifierCV(estimator=base_svc, cv=3)

    pipeline = Pipeline([
        ("tfidf", vectorizer),
        ("clf", calibrated_svc),
    ])

    logger.info("Training model...")
    pipeline.fit(X_full_train, y_full_train)

    logger.info("Evaluating on test set (%d samples)...", len(X_test))
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=sorted(list(set(y_test))))

    logger.info("Test Accuracy: %.4f (%.2f%%)", acc, acc * 100)
    print("\n" + "=" * 60)
    print("CLASSIFICATION REPORT (Baseline TF-IDF + SVM)")
    print("=" * 60)
    print(report)
    print("=" * 60 + "\n")

    logger.info("Saving model to %s...", MODEL_OUTPUT_PATH)
    joblib.dump(pipeline, MODEL_OUTPUT_PATH, compress=3)
    logger.info("Model saved successfully (%d bytes)", MODEL_OUTPUT_PATH.stat().st_size)

    # Test sample inference
    samples = [
        "J'ai passé un moment absolument merveilleux et magique avec mes amis !",
        "Je me sens tellement triste et dévasté, tout s'effondre autour de moi.",
        "C'est inadmissible, ce comportement irrespectueux me met hors de moi !",
        "J'ai tellement peur de ce qui pourrait arriver demain, je tremble.",
        "Je n'en reviens pas, quelle incroyable surprise inattendue !",
        "Cette nourriture a une odeur infecte et écœurante, ça me répugne.",
        "Aujourd'hui j'ai fait mes courses et nettoyé le salon, rien de spécial.",
    ]
    print("\nSAMPLE PREDICTIONS:")
    for s in samples:
        pred = pipeline.predict([s])[0]
        probs = pipeline.predict_proba([s])[0]
        conf = max(probs)
        print(f"[{pred.upper():<10}] ({conf:.1%}) -> {s}")

    return pipeline, acc


if __name__ == "__main__":
    train_baseline()
