"""
MemoAi — Classify Existing Entries Management Command
Runs the trained emotion classification model on all journal entries in the database.

Usage:
    python manage.py classify_emotions [--all] [--user email]
"""

from django.core.management.base import BaseCommand
from journal.models import JournalEntry
from ai.models import AIAnalysis
from ai.services.emotion_service import classify_emotion, EMOTION_META


class Command(BaseCommand):
    help = "Classify emotions of journal entries using the trained ML model."

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Re-classify all entries, even those already classified.',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Only classify entries belonging to this user email.',
        )

    def handle(self, *args, **options):
        reclassify_all = options.get('all', False)
        user_email = options.get('user')

        qs = JournalEntry.objects.filter(deleted_at__isnull=True).exclude(content='')
        if user_email:
            qs = qs.filter(user__email=user_email)

        self.stdout.write(self.style.NOTICE(f"Found {qs.count()} candidate entries."))

        count_updated = 0
        counts_by_emotion = {k: 0 for k in EMOTION_META}

        for entry in qs.select_related('ai_analysis', 'user'):
            content = (entry.content or '').strip()
            if not content:
                continue

            analysis, _ = AIAnalysis.objects.get_or_create(entry=entry)

            if analysis.emotion and not reclassify_all:
                continue

            lang = getattr(getattr(entry.user, 'preferences', None), 'language', 'fr') or 'fr'
            res = classify_emotion(content, lang=lang, user_mood=entry.mood)

            analysis.emotion = res['emotion']
            analysis.emotion_score = res['score']
            analysis.emotion_status = 'completed'
            analysis.save(update_fields=['emotion', 'emotion_score', 'emotion_status'])

            counts_by_emotion[res['emotion']] = counts_by_emotion.get(res['emotion'], 0) + 1
            count_updated += 1

            self.stdout.write(
                f"  [{res['emotion'].upper():<9}] (score={res['score']:.2f}) -> {entry.title or 'Sans titre'} ({entry.entry_date})"
            )

        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully classified {count_updated} entries!"))
        self.stdout.write("Distribution:")
        for emo, count in counts_by_emotion.items():
            meta = EMOTION_META.get(emo, {})
            emo_name = meta.get('fr', emo)
            self.stdout.write(f"  - {emo_name:<10} : {count}")

