"""
MemoAi — Churn Dataset Generator
================================
Génère un dataset réaliste pour l'entraînement du modèle de prédiction du churn.
Le dataset combine :
- Les profils extraits de la base de données réelle (s'ils existent)
- Des cohortes comportementales synthétiques modélisant :
  * Utilisateurs actifs et fidèles (Churn = 0)
  * Nouveaux utilisateurs en phase d'onboarding (Churn = 0)
  * Utilisateurs en perte de vitesse / déclin d'interaction (Churn = 1)
  * Utilisateurs inactifs / décrochés (Churn = 1)

Usage :
    python ai/ml/generate_churn_dataset.py [--count 2500] [--output ai/ml/data/churn_dataset.csv]
"""

import os
import sys
import csv
import random
import argparse
from pathlib import Path

# Setup Django if possible to pull real users
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    DJANGO_AVAILABLE = True
except Exception:
    DJANGO_AVAILABLE = False

from ai.ml.churn_features import FEATURE_NAMES, extract_user_features


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_OUTPUT_CSV = DATA_DIR / "churn_dataset.csv"


def generate_synthetic_user(cohort_type):
    """
    Génère un profil utilisateur réaliste selon sa cohorte comportementale.
    Cohortes :
    - 'power_user'   : Très actif, notes quotidiennes, forte utilisation IA (Churn = 0)
    - 'regular'      : Actif régulier, 2-4 notes/semaine (Churn = 0)
    - 'new_active'   : Nouveau compte actif (1-15 jours) (Churn = 0)
    - 'declining'    : Activité en chute libre, risque imminent de départ (Churn = 1)
    - 'churned'      : Inactif depuis > 25 jours (Churn = 1)
    - 'abandoned'    : Compte créé avec 0 ou 1 entrée puis abandonné (Churn = 1)
    """
    if cohort_type == 'power_user':
        account_age = random.randint(30, 365)
        days_login = random.randint(0, 2)
        days_entry = random.randint(0, 3)
        entries_7d = random.randint(4, 9)
        entries_30d = random.randint(18, 35)
        total_entries = int(entries_30d * (account_age / 30.0) * random.uniform(0.7, 1.2))
        total_entries = max(entries_30d, total_entries)
        drop_ratio = random.uniform(0.0, 0.2)
        avg_words = random.randint(80, 250)
        total_words = total_entries * avg_words
        media_count = int(total_entries * random.uniform(0.3, 0.9))
        audio_count = int(media_count * random.uniform(0.1, 0.4))
        ai_analyses = int(total_entries * random.uniform(0.5, 0.95))
        negative_ratio = random.uniform(0.05, 0.35)
        is_churn = 0

    elif cohort_type == 'regular':
        account_age = random.randint(20, 250)
        days_login = random.randint(0, 5)
        days_entry = random.randint(1, 6)
        entries_7d = random.randint(1, 4)
        entries_30d = random.randint(6, 16)
        total_entries = int(entries_30d * (account_age / 30.0) * random.uniform(0.6, 1.0))
        total_entries = max(entries_30d, total_entries)
        drop_ratio = random.uniform(0.0, 0.35)
        avg_words = random.randint(40, 150)
        total_words = total_entries * avg_words
        media_count = int(total_entries * random.uniform(0.1, 0.5))
        audio_count = int(media_count * random.uniform(0.0, 0.3))
        ai_analyses = int(total_entries * random.uniform(0.2, 0.7))
        negative_ratio = random.uniform(0.1, 0.4)
        is_churn = 0

    elif cohort_type == 'new_active':
        account_age = random.randint(2, 14)
        days_login = random.randint(0, 2)
        days_entry = random.randint(0, 3)
        entries_7d = random.randint(2, 6)
        entries_30d = entries_7d
        total_entries = entries_7d
        drop_ratio = random.uniform(0.0, 0.15)
        avg_words = random.randint(50, 180)
        total_words = total_entries * avg_words
        media_count = random.randint(0, 3)
        audio_count = 1 if random.random() < 0.3 else 0
        ai_analyses = random.randint(1, total_entries)
        negative_ratio = random.uniform(0.05, 0.3)
        is_churn = 0

    elif cohort_type == 'declining':
        account_age = random.randint(25, 200)
        days_login = random.randint(8, 22)
        days_entry = random.randint(12, 28)
        entries_7d = random.choice([0, 0, 1])
        entries_30d = random.randint(0, 3)
        total_entries = random.randint(6, 45)
        drop_ratio = random.uniform(0.65, 0.98)
        avg_words = random.randint(25, 100)
        total_words = total_entries * avg_words
        media_count = random.randint(0, 4)
        audio_count = 0
        ai_analyses = random.randint(0, int(total_entries * 0.3))
        negative_ratio = random.uniform(0.2, 0.7)  # Sentiment souvent plus négatif avant churn
        is_churn = 1

    elif cohort_type == 'churned':
        account_age = random.randint(40, 365)
        days_login = random.randint(25, 120)
        days_entry = random.randint(30, 150)
        entries_7d = 0
        entries_30d = random.choice([0, 0, 0, 1])
        total_entries = random.randint(3, 30)
        drop_ratio = 1.0
        avg_words = random.randint(15, 80)
        total_words = total_entries * avg_words
        media_count = random.randint(0, 2)
        audio_count = 0
        ai_analyses = random.randint(0, 3)
        negative_ratio = random.uniform(0.25, 0.8)
        is_churn = 1

    else:  # 'abandoned'
        account_age = random.randint(15, 180)
        days_login = random.randint(14, account_age)
        days_entry = account_age
        entries_7d = 0
        entries_30d = 0
        total_entries = random.choice([0, 1])
        drop_ratio = 1.0
        avg_words = random.randint(0, 40)
        total_words = total_entries * avg_words
        media_count = 0
        audio_count = 0
        ai_analyses = 0
        negative_ratio = 0.0
        is_churn = 1

    entry_freq = round(total_entries / max(1, account_age), 4)
    ai_rate = round(ai_analyses / max(1, total_entries), 3)

    return {
        "account_age_days": float(account_age),
        "days_since_last_login": float(days_login),
        "days_since_last_entry": float(days_entry),
        "total_entries": float(total_entries),
        "entries_last_7d": float(entries_7d),
        "entries_last_30d": float(entries_30d),
        "entry_frequency": float(entry_freq),
        "activity_drop_ratio": float(round(drop_ratio, 4)),
        "total_words": float(total_words),
        "avg_words_per_entry": float(avg_words),
        "media_count": float(media_count),
        "has_audio_entries": float(audio_count),
        "ai_analyses_count": float(ai_analyses),
        "ai_usage_rate": float(ai_rate),
        "negative_mood_ratio": float(round(negative_ratio, 3)),
        "is_churn": int(is_churn),
    }


def generate_dataset(total_samples=2500, output_path=DEFAULT_OUTPUT_CSV):
    """Génère le dataset complet avec équilibre réaliste des cohortes."""
    rows = []

    # 1. Extraire les utilisateurs réels si Django est connecté
    real_count = 0
    if DJANGO_AVAILABLE:
        try:
            from accounts.models import User
            for user in User.objects.all():
                feats = extract_user_features(user)
                # Heuristique pour le label réel : inactif depuis > 18 jours ou 0 entrée depuis 14j
                is_churn = 1 if (feats["days_since_last_login"] > 18 or feats["days_since_last_entry"] > 21) else 0
                feats["is_churn"] = is_churn
                rows.append(feats)
                real_count += 1
            print(f"[Dataset] {real_count} utilisateurs reels extraits de la base.")
        except Exception as e:
            print(f"[Dataset] Info: Extraction des utilisateurs reels ignoree ({e}).")

    # 2. Compléter avec les cohortes synthétiques
    remaining = max(0, total_samples - real_count)
    cohort_weights = {
        'power_user': int(remaining * 0.18),
        'regular':    int(remaining * 0.32),
        'new_active': int(remaining * 0.10),
        'declining':  int(remaining * 0.20),
        'churned':    int(remaining * 0.12),
        'abandoned':  int(remaining * 0.08),
    }

    for cohort, count in cohort_weights.items():
        for _ in range(count):
            rows.append(generate_synthetic_user(cohort))

    random.shuffle(rows)

    # 3. Écrire le CSV
    columns = FEATURE_NAMES + ["is_churn"]
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    churned_count = sum(1 for r in rows if r["is_churn"] == 1)
    retained_count = len(rows) - churned_count

    print(f"[Dataset] Fichier genere avec succes : {output_path}")
    print(f"[Dataset] Total exemples : {len(rows)} (Churn: {churned_count} [{churned_count*100/len(rows):.1f}%], Actifs: {retained_count} [{retained_count*100/len(rows):.1f}%])")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genere un dataset de churn pour MemoAi")
    parser.add_argument("--count", type=int, default=2500, help="Nombre total d'exemples")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_CSV), help="Chemin du fichier CSV de sortie")
    args = parser.parse_args()

    generate_dataset(total_samples=args.count, output_path=args.output)
