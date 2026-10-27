"""
MemoAi — Churn Prediction Feature Extraction
============================================
Extrait les caractéristiques comportementales d'un utilisateur sur la plateforme
pour alimenter le modèle de prédiction du churn (attrition).

Features calculées :
1.  account_age_days          : Ancienneté du compte en jours
2.  days_since_last_login     : Jours écoulés depuis la dernière connexion
3.  days_since_last_entry     : Jours écoulés depuis la dernière note de journal
4.  total_entries             : Nombre total de notes de journal rédigées
5.  entries_last_7d           : Nombre de notes rédigées les 7 derniers jours
6.  entries_last_30d          : Nombre de notes rédigées les 30 derniers jours
7.  entry_frequency           : Fréquence moyenne de rédaction par jour (total / âge)
8.  activity_drop_ratio       : Ratio d'activité récente vs historique (décroissance)
9.  total_words               : Volume total de mots écrits
10. avg_words_per_entry       : Longueur moyenne d'une note (mots)
11. media_count               : Nombre total de médias uploadés (photos, audios, vidéos)
12. has_audio_entries         : Nombre de notes vocales enregistrées
13. ai_analyses_count         : Nombre d'analyses d'intelligence artificielle réalisées
14. ai_usage_rate             : Taux d'utilisation de l'IA par note (analyses / notes)
15. negative_mood_ratio       : Proportion d'entrées associées à une humeur difficile/négative
"""

from datetime import timedelta
from django.utils import timezone

FEATURE_NAMES = [
    "account_age_days",
    "days_since_last_login",
    "days_since_last_entry",
    "total_entries",
    "entries_last_7d",
    "entries_last_30d",
    "entry_frequency",
    "activity_drop_ratio",
    "total_words",
    "avg_words_per_entry",
    "media_count",
    "has_audio_entries",
    "ai_analyses_count",
    "ai_usage_rate",
    "negative_mood_ratio",
]

NEGATIVE_MOODS = {'sad', 'stressed', 'anxious', 'angry', 'tired'}


def extract_user_features(user, reference_date=None):
    """
    Extrait le dictionnaire de features pour un utilisateur donné à une date de référence.
    Si reference_date est None, utilise timezone.now().
    """
    from journal.models import JournalEntry
    from media_app.models import Media
    from ai.models import AIAnalysis

    now = reference_date or timezone.now()
    user_created = user.created_at if hasattr(user, 'created_at') and user.created_at else now
    account_age_days = max(1, (now - user_created).days)

    # 1. Connexion
    if user.last_login:
        days_since_last_login = max(0, (now - user.last_login).days)
    else:
        days_since_last_login = account_age_days

    # 2. Entrées de journal
    entries_qs = JournalEntry.objects.filter(user=user, deleted_at__isnull=True)
    total_entries = entries_qs.count()

    latest_entry = entries_qs.order_by('-entry_date', '-created_at').first()
    if latest_entry:
        entry_dt = timezone.make_aware(timezone.datetime.combine(latest_entry.entry_date, timezone.datetime.min.time())) if timezone.is_naive(timezone.datetime.combine(latest_entry.entry_date, timezone.datetime.min.time())) else latest_entry.created_at
        days_since_last_entry = max(0, (now.date() - latest_entry.entry_date).days)
    else:
        days_since_last_entry = account_age_days

    date_7d_ago = (now - timedelta(days=7)).date()
    date_30d_ago = (now - timedelta(days=30)).date()

    entries_last_7d = entries_qs.filter(entry_date__gte=date_7d_ago).count()
    entries_last_30d = entries_qs.filter(entry_date__gte=date_30d_ago).count()

    entry_frequency = round(total_entries / max(1, account_age_days), 4)

    # Ratio de baisse d'activité : activité attendue sur 30j vs activité réelle
    expected_30d = (total_entries / max(30, account_age_days)) * 30
    if expected_30d > 0:
        activity_drop_ratio = round(max(0.0, 1.0 - (entries_last_30d / expected_30d)), 4)
    else:
        activity_drop_ratio = 1.0 if total_entries == 0 else 0.0

    # 3. Mots rédigés
    from django.db.models import Sum
    words_sum = entries_qs.aggregate(total_w=Sum('word_count'))['total_w'] or 0
    total_words = int(words_sum)
    avg_words_per_entry = round(total_words / max(1, total_entries), 1)

    # 4. Médias
    entry_ids = list(entries_qs.values_list('id', flat=True))
    media_count = Media.objects.filter(entry_id__in=entry_ids).count()
    has_audio_entries = Media.objects.filter(entry_id__in=entry_ids, media_type='AUDIO').count()

    # 5. Analyses IA
    ai_analyses_count = AIAnalysis.objects.filter(entry_id__in=entry_ids, is_successful=True).count()
    ai_usage_rate = round(ai_analyses_count / max(1, total_entries), 3)

    # 6. Humeurs négatives
    negative_count = entries_qs.filter(mood__in=NEGATIVE_MOODS).count()
    negative_mood_ratio = round(negative_count / max(1, total_entries), 3)

    return {
        "account_age_days": float(account_age_days),
        "days_since_last_login": float(days_since_last_login),
        "days_since_last_entry": float(days_since_last_entry),
        "total_entries": float(total_entries),
        "entries_last_7d": float(entries_last_7d),
        "entries_last_30d": float(entries_last_30d),
        "entry_frequency": float(entry_frequency),
        "activity_drop_ratio": float(activity_drop_ratio),
        "total_words": float(total_words),
        "avg_words_per_entry": float(avg_words_per_entry),
        "media_count": float(media_count),
        "has_audio_entries": float(has_audio_entries),
        "ai_analyses_count": float(ai_analyses_count),
        "ai_usage_rate": float(ai_usage_rate),
        "negative_mood_ratio": float(negative_mood_ratio),
    }


def features_to_vector(features_dict):
    """Convertit un dictionnaire de features en liste ordonnée selon FEATURE_NAMES."""
    return [features_dict[name] for name in FEATURE_NAMES]
