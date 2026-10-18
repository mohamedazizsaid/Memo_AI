"""
MemoAi — Reset Demo Data Command

Removes every fabricated ("mock") record the old seeder used to create — entries,
tags, people, face detections, notifications and their AI analyses — while keeping
the demo account itself.

From now on MemoAI only ever shows *real* AI results: create an entry through the
journal editor and the Gemini analysis + the free illustration run for real.
"""

from django.core.management.base import BaseCommand

from accounts.models import User, UserPreferences
from journal.models import JournalEntry
from tags.models import Tag
from persons.models import Person, FaceDetection
from media_app.models import Media
from ai.models import AIAnalysis
from notifications.models import Notification


class Command(BaseCommand):
    help = 'Deletes all seeded/mock journal data for the demo account (keeps the account).'

    def add_arguments(self, parser):
        parser.add_argument('--email', default='demo@memoai.local')
        parser.add_argument('--password', default='DemoPass123!')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']

        user, created = User.objects.get_or_create(
            email=email,
            defaults={'first_name': 'Sophie', 'last_name': 'Bernard'},
        )
        user.set_password(password)
        user.save()
        UserPreferences.objects.get_or_create(user=user)

        if created:
            self.stdout.write(f'Created demo account {email}')

        counts = {
            'entries': JournalEntry.objects.filter(user=user).count(),
            'analyses': AIAnalysis.objects.filter(entry__user=user).count(),
            'media': Media.objects.filter(entry__user=user).count(),
            'face_detections': FaceDetection.objects.filter(media__entry__user=user).count(),
            'people': Person.objects.filter(user=user).count(),
            'tags': Tag.objects.filter(user=user).count(),
            'notifications': Notification.objects.filter(user=user).count(),
        }

        # Cascades: entry → media → face detections, entry → ai_analysis.
        JournalEntry.objects.filter(user=user).delete()
        Person.objects.filter(user=user).delete()
        Tag.objects.filter(user=user).delete()
        Notification.objects.filter(user=user).delete()

        self.stdout.write(self.style.SUCCESS(
            f'Mock data removed for {email}: ' + ', '.join(f'{v} {k}' for k, v in counts.items())
        ))
        self.stdout.write('The demo account is now clean — real AI analysis will populate it.')
