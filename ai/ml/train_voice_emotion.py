"""
MemoAi — Voice Emotion Classifier Training
===========================================
Entraîne un modèle Random Forest (+ SVM comme baseline) sur des caractéristiques
audio extraites avec librosa, à partir des datasets RAVDESS et CREMA-D.

Émotions supportées (mappées sur les 7 classes MemoAi) :
    neutral   → neutre
    calm      → neutre
    happy     → joie
    sad       → tristesse
    angry     → colere
    fearful   → peur
    disgust   → degout
    surprised → surprise

Usage :
    # Entraînement rapide sans téléchargement (données synthétiques)
    python ai/ml/train_voice_emotion.py --demo

    # Télécharger CREMA-D + entraîner
    python ai/ml/train_voice_emotion.py --download-cremad

    # RAVDESS fourni manuellement
    python ai/ml/train_voice_emotion.py --ravdess-dir /chemin/vers/ravdess

    # Choisir le modèle
    python ai/ml/train_voice_emotion.py --model svm   (SVM RBF)
    python ai/ml/train_voice_emotion.py --model rf    (Random Forest — défaut)
    python ai/ml/train_voice_emotion.py --model mlp   (MLP)

Dépendances :
    pip install librosa soundfile scikit-learn joblib numpy requests

Datasets :
    RAVDESS : https://zenodo.org/records/1188976
    CREMA-D : https://github.com/CheyneyComputerScience/CREMA-D
"""

import argparse
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import requests

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Chemins ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
DATA_DIR   = BASE_DIR / "data" / "voice"
MODELS_DIR = BASE_DIR / "models"
MODEL_PATH = MODELS_DIR / "voice_emotion_rf.joblib"

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── Mapping émotion → classe MemoAi ────────────────────────────────────────────
# RAVDESS : code 2 du nom de fichier (ex: 03-01-05-01-01-01-12.wav → "05" = colere)
RAVDESS_EMOTION_MAP = {
    "01": "neutre",
    "02": "neutre",    # calm → neutre
    "03": "joie",
    "04": "tristesse",
    "05": "colere",
    "06": "peur",
    "07": "degout",
    "08": "surprise",
}

# CREMA-D : code 3 du nom de fichier (ex: 1001_DFA_ANG_XX.wav → "ANG" = colere)
CREMAD_EMOTION_MAP = {
    "NEU": "neutre",
    "HAP": "joie",
    "SAD": "tristesse",
    "ANG": "colere",
    "FEA": "peur",
    "DIS": "degout",
}

EMOTION_CLASSES = ["neutre", "joie", "tristesse", "colere", "peur", "degout", "surprise"]

# ── Extraction de features audio ───────────────────────────────────────────────

def extract_features(audio_path: str, sr: int = 22050, duration: float = 3.0):
    """
    Extrait un vecteur de 364 features audio depuis un fichier.

    Composition du vecteur :
        - 40 MFCC mean + 40 MFCC std       = 80 valeurs  (timbre/phonétique)
        - 12 Chroma mean + 12 Chroma std   = 24 valeurs  (profil tonal)
        - 1 ZCR mean + 1 ZCR std           = 2  valeurs  (voisement)
        - 1 RMS mean + 1 RMS std           = 2  valeurs  (intensité)
        - 128 Mel mean + 128 Mel std        = 256 valeurs (spectrogramme)
                                             ───────────
                                             364 valeurs totales
    """
    try:
        import librosa
    except ImportError:
        raise ImportError("librosa est requis : pip install librosa soundfile")

    try:
        y, sr = librosa.load(audio_path, sr=sr, duration=duration, mono=True)
    except Exception as exc:
        logger.debug("Impossible de charger %s : %s", audio_path, exc)
        return None

    if len(y) < sr * 0.5:
        return None

    feats = []

    # MFCCs
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
    feats.extend([np.mean(mfccs, axis=1), np.std(mfccs, axis=1)])

    # Chroma
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    feats.extend([np.mean(chroma, axis=1), np.std(chroma, axis=1)])

    # Zero Crossing Rate
    zcr = librosa.feature.zero_crossing_rate(y)
    feats.append([np.mean(zcr), np.std(zcr)])

    # RMS Energy
    rms = librosa.feature.rms(y=y)
    feats.append([np.mean(rms), np.std(rms)])

    # Mel Spectrogram
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    feats.extend([np.mean(mel_db, axis=1), np.std(mel_db, axis=1)])

    return np.concatenate([np.atleast_1d(f) for f in feats]).astype(np.float32)


# ── Parsing noms de fichiers ────────────────────────────────────────────────────

def parse_ravdess_label(filename: str):
    parts = Path(filename).stem.split("-")
    if len(parts) >= 3:
        return RAVDESS_EMOTION_MAP.get(parts[2])
    return None


def parse_cremad_label(filename: str):
    parts = Path(filename).stem.split("_")
    if len(parts) >= 3:
        return CREMAD_EMOTION_MAP.get(parts[2].upper())
    return None


# ── Chargement des datasets ─────────────────────────────────────────────────────

def load_dataset_dir(audio_dir: Path, label_fn) -> tuple:
    """Charge tous les WAV d'un dossier avec la fonction de parsing fournie."""
    X, y = [], []
    wav_files = list(audio_dir.rglob("*.wav"))
    logger.info("%d fichiers WAV dans %s", len(wav_files), audio_dir)
    for wav in wav_files:
        label = label_fn(wav.name)
        if not label:
            continue
        feat = extract_features(str(wav))
        if feat is not None:
            X.append(feat)
            y.append(label)
    logger.info("Chargé : %d échantillons valides", len(X))
    return X, y


# ── Dataset synthétique pour tests de l'infra ──────────────────────────────────

def generate_demo_features(n_samples: int = 700, seed: int = 42) -> tuple:
    """
    Features synthétiques par émotion (distributions gaussiennes séparées).

    ⚠ Ce modèle ne peut PAS être utilisé en production.
    Il sert uniquement à valider l'infrastructure sans télécharger les datasets.
    """
    rng = np.random.RandomState(seed)
    dim = 364
    centers = {
        "joie":      rng.randn(dim) * 0.8 + 1.2,
        "tristesse": rng.randn(dim) * 0.8 - 1.2,
        "colere":    rng.randn(dim) * 1.2 + 0.6,
        "peur":      rng.randn(dim) * 1.0 - 0.6,
        "degout":    rng.randn(dim) * 0.9 - 0.9,
        "surprise":  rng.randn(dim) * 1.1 + 0.4,
        "neutre":    rng.randn(dim) * 0.4,
    }
    X, y = [], []
    per_class = n_samples // len(EMOTION_CLASSES)
    for emo, center in centers.items():
        for _ in range(per_class):
            X.append(center + rng.randn(dim) * 0.5)
            y.append(emo)
    idx = rng.permutation(len(X))
    return np.array(X)[idx], [y[i] for i in idx]


# ── Téléchargement CREMA-D ─────────────────────────────────────────────────────

def download_cremad(target_dir: Path, max_files: int = 2000) -> Path:
    """
    Télécharge un sous-ensemble de CREMA-D depuis GitHub.
    URL: https://github.com/CheyneyComputerScience/CREMA-D (AudioWAV/)
    """
    out = target_dir / "cremad_audio"
    out.mkdir(parents=True, exist_ok=True)

    existing = [f for f in out.glob("*.wav") if f.stat().st_size > 1000]
    if len(existing) >= max_files:
        logger.info("CREMA-D déjà présent (%d fichiers audio valides)", len(existing))
        return out

    logger.info("Récupération de l'index CREMA-D via l'API GitHub...")
    api_url = (
        "https://api.github.com/repos/CheyneyComputerScience/CREMA-D"
        "/git/trees/master?recursive=1"
    )
    try:
        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
        tree = resp.json().get("tree", [])
    except Exception as exc:
        logger.error("Impossible de récupérer l'index : %s", exc)
        return out

    wav_items = [
        item for item in tree
        if item.get("path", "").startswith("AudioWAV/") and item["path"].endswith(".wav")
    ][:max_files]

    # Utilisation de media.githubusercontent.com pour résoudre les fichiers binaires Git LFS
    base_media = "https://media.githubusercontent.com/media/CheyneyComputerScience/CREMA-D/master/"
    logger.info("Téléchargement de %d fichiers WAV CREMA-D réels (Git LFS)...", len(wav_items))

    for i, item in enumerate(wav_items):
        fname = Path(item["path"]).name
        dest = out / fname
        if dest.exists() and dest.stat().st_size > 1000:
            continue
        try:
            r = requests.get(base_media + item["path"], timeout=30)
            r.raise_for_status()
            # Vérifier que le contenu commence bien par RIFF (vrai fichier WAV, pas un pointeur LFS)
            if r.content.startswith(b"RIFF"):
                dest.write_bytes(r.content)
            else:
                logger.warning("Fichier non WAV reçu pour %s (taille %d)", fname, len(r.content))
        except Exception as exc:
            logger.debug("Echec %s : %s", fname, exc)
        if (i + 1) % 50 == 0:
            logger.info("  %d / %d téléchargés", i + 1, len(wav_items))

    valid_wavs = [f for f in out.glob("*.wav") if f.stat().st_size > 1000]
    logger.info("CREMA-D : %d fichiers audio valides disponibles", len(valid_wavs))
    return out


# ── Construction du pipeline sklearn ───────────────────────────────────────────

def build_pipeline(model_type: str = "rf"):
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    if model_type == "rf":
        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(
            n_estimators=300,
            max_features="sqrt",
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
    elif model_type == "svm":
        from sklearn.svm import SVC
        from sklearn.calibration import CalibratedClassifierCV
        clf = CalibratedClassifierCV(
            SVC(kernel="rbf", C=10, gamma="scale", random_state=42), cv=3
        )
    elif model_type == "mlp":
        from sklearn.neural_network import MLPClassifier
        clf = MLPClassifier(
            hidden_layer_sizes=(256, 128, 64),
            max_iter=500,
            early_stopping=True,
            random_state=42,
        )
    else:
        raise ValueError(f"Modèle inconnu : {model_type}")

    return Pipeline([("scaler", StandardScaler()), ("clf", clf)])


# ── Entraînement principal ──────────────────────────────────────────────────────

def train_voice_emotion(args):
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import cross_val_score, train_test_split

    # ── Collecte des données ────────────────────────────────────────────────────
    X_all, y_all = [], []

    if args.demo:
        logger.info("=== Mode démonstration (features synthétiques) ===")
        Xd, yd = generate_demo_features(n_samples=args.demo_samples)
        X_all.extend(Xd)
        y_all.extend(yd)

    else:
        # RAVDESS
        ravdess_dir = Path(args.ravdess_dir) if args.ravdess_dir else DATA_DIR / "ravdess"
        if ravdess_dir.exists():
            Xr, yr = load_dataset_dir(ravdess_dir, parse_ravdess_label)
            X_all.extend(Xr); y_all.extend(yr)
            logger.info("RAVDESS : %d échantillons ajoutés", len(Xr))
        else:
            logger.warning(
                "Dossier RAVDESS introuvable : %s\n"
                "→ Téléchargez depuis https://zenodo.org/records/1188976\n"
                "→ Extrayez dans %s ou utilisez --ravdess-dir",
                ravdess_dir, DATA_DIR / "ravdess"
            )

        # CREMA-D
        cremad_dir = Path(args.cremad_dir) if args.cremad_dir else DATA_DIR / "cremad"
        if cremad_dir.exists():
            Xc, yc = load_dataset_dir(cremad_dir, parse_cremad_label)
            X_all.extend(Xc); y_all.extend(yc)
            logger.info("CREMA-D (manuel) : %d échantillons ajoutés", len(Xc))
        elif args.download_cremad:
            cremad_audio = download_cremad(DATA_DIR, max_files=args.cremad_max_files)
            Xc, yc = load_dataset_dir(cremad_audio, parse_cremad_label)
            X_all.extend(Xc); y_all.extend(yc)
            logger.info("CREMA-D (téléchargé) : %d échantillons ajoutés", len(Xc))
        else:
            logger.warning(
                "CREMA-D non trouvé. Utilisez --download-cremad ou --cremad-dir."
            )

    if not X_all:
        logger.error(
            "Aucune donnée. Exemples d'usage :\n"
            "  python train_voice_emotion.py --demo\n"
            "  python train_voice_emotion.py --download-cremad\n"
            "  python train_voice_emotion.py --ravdess-dir /chemin"
        )
        sys.exit(1)

    X = np.array(X_all, dtype=np.float32)
    y = np.array(y_all)

    logger.info("Dataset : %d échantillons × %d features", *X.shape)
    for emo, cnt in zip(*np.unique(y, return_counts=True)):
        logger.info("  %-12s : %d", emo, cnt)

    # ── Train / Test split ──────────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    logger.info("Split : %d train | %d test", len(X_train), len(X_test))

    # ── Entraînement ────────────────────────────────────────────────────────────
    logger.info("Modèle : %s — entraînement...", args.model.upper())
    pipeline = build_pipeline(args.model)
    pipeline.fit(X_train, y_train)

    # ── Évaluation ──────────────────────────────────────────────────────────────
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    logger.info("Test Accuracy : %.2f%%", acc * 100)

    print("\n" + "=" * 65)
    print(f"  RAPPORT — Voice Emotion ({args.model.upper()})  |  Acc: {acc:.2%}")
    print("=" * 65)
    print(classification_report(y_test, y_pred, target_names=sorted(set(y_test)), zero_division=0))
    print("=" * 65)

    if not args.skip_cv and len(X_all) <= 6000:
        logger.info("Validation croisée 3-fold...")
        cv = cross_val_score(pipeline, X, y, cv=3, scoring="accuracy", n_jobs=-1)
        logger.info("CV : %.2f%% ± %.2f%%", cv.mean() * 100, cv.std() * 100)

    # ── Sauvegarde ──────────────────────────────────────────────────────────────
    named_path = MODELS_DIR / f"voice_emotion_{args.model}.joblib"
    joblib.dump(pipeline, named_path, compress=3)
    logger.info("Modèle sauvegardé : %s (%d octets)", named_path, named_path.stat().st_size)

    if args.model == "rf":
        joblib.dump(pipeline, MODEL_PATH, compress=3)
        logger.info("Chemin canonique : %s", MODEL_PATH)

    # ── Inférence de démonstration ──────────────────────────────────────────────
    print("\nEXEMPLES D'INFÉRENCE (3 échantillons de test) :")
    for i in range(min(3, len(X_test))):
        proba = pipeline.predict_proba([X_test[i]])[0]
        pred  = pipeline.classes_[np.argmax(proba)]
        conf  = np.max(proba)
        print(f"  Réel: {y_test[i]:<12} | Prédit: {pred:<12} | Confiance: {conf:.1%}")

    return pipeline, acc


# ── CLI ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Entraîne un classificateur d'émotions vocales (RAVDESS + CREMA-D).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ravdess-dir",      type=str,  default=None)
    parser.add_argument("--cremad-dir",       type=str,  default=None)
    parser.add_argument("--download-cremad",  action="store_true",
                        help="Télécharger CREMA-D automatiquement depuis GitHub")
    parser.add_argument("--cremad-max-files", type=int,  default=2000)
    parser.add_argument("--demo",             action="store_true",
                        help="Mode démo : features synthétiques (sans audio réel)")
    parser.add_argument("--demo-samples",     type=int,  default=700)
    parser.add_argument("--model",            type=str,  default="rf",
                        choices=["rf", "svm", "mlp"])
    parser.add_argument("--skip-cv",          action="store_true")
    args = parser.parse_args()
    train_voice_emotion(args)
