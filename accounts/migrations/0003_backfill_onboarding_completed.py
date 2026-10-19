"""
MemoAi — backfill for existing accounts.

Accounts created before the animated onboarding shipped must not be sent
through it; only new registrations (starting from this release) get the tour.
"""

from django.db import migrations
from django.utils import timezone


def mark_existing_completed(apps, schema_editor):
    UserPreferences = apps.get_model('accounts', 'UserPreferences')
    UserPreferences.objects.filter(onboarding_completed=False).update(
        onboarding_completed=True,
        onboarding_completed_at=timezone.now(),
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_userpreferences_gender_and_more'),
    ]

    operations = [
        migrations.RunPython(mark_existing_completed, noop),
    ]
