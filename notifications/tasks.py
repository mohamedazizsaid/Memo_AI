"""
MemoAi — Notifications Celery Tasks
Scheduled tasks for daily reminders, nostalgic flashbacks, and weekly/monthly summaries.
"""

import logging
from datetime import date, timedelta
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from accounts.models import User
from journal.models import JournalEntry
from .models import Notification

logger = logging.getLogger('memoai')


@shared_task(name='notifications.tasks.send_daily_memory_reminder')
def send_daily_memory_reminder():
    """
    Daily reminder & nostalgia check for active users.
    1. Checks for memories from exact same day in previous years (On This Day).
    2. If no nostalgia memory, checks if the user hasn't written today and sends an inspirational prompt.
    """
    today = timezone.now().date()
    users = User.objects.filter(
        is_active=True,
        preferences__daily_reminder_enabled=True,
    ).select_related('preferences')

    count = 0
    for user in users:
        try:
            # 1. Check nostalgia memory (1, 2, 3, 5 years ago)
            past_years_entries = JournalEntry.objects.filter(
                user=user,
                entry_date__month=today.month,
                entry_date__day=today.day,
                entry_date__year__lt=today.year,
            ).order_by('-entry_date')

            if past_years_entries.exists():
                flashback = past_years_entries.first()
                years_ago = today.year - flashback.entry_date.year
                title = f"Flashback : Il y a {years_ago} an{'s' if years_ago > 1 else ''}"
                message = f"Revisitez vos souvenirs du {flashback.entry_date.strftime('%d/%m/%Y')} : « {flashback.title or flashback.excerpt[:50]} »"

                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    notification_type='memory_nostalgia',
                    data={'entry_id': str(flashback.id)},
                )

                if user.preferences.email_notifications:
                    send_mail(
                        subject=f"[MemoAi] {title}",
                        message=f"{message}\n\nAccédez à votre souvenir sur MemoAi : {settings.FRONTEND_URL}/entries/{flashback.id}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
                count += 1
            else:
                # 2. Check if user wrote today
                has_written_today = JournalEntry.objects.filter(
                    user=user,
                    entry_date=today,
                ).exists()

                if not has_written_today:
                    title = "Votre journée attend son souvenir ✍️"
                    message = "Prenez 2 minutes pour immortaliser vos pensées, vos réussites ou votre humeur du jour."
                    Notification.objects.create(
                        user=user,
                        title=title,
                        message=message,
                        notification_type='daily_reminder',
                        data={'action': 'create_entry'},
                    )
                    count += 1
        except Exception as e:
            logger.error(f"Error sending daily reminder to user {user.id}: {e}")

    logger.info(f"Daily reminders dispatched to {count} users.")
    return count


@shared_task(name='notifications.tasks.send_weekly_summary')
def send_weekly_summary():
    """
    Weekly recap notification sent every Monday.
    """
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    users = User.objects.filter(
        is_active=True,
        preferences__weekly_summary_enabled=True,
    ).select_related('preferences')

    count = 0
    for user in users:
        try:
            entry_count = JournalEntry.objects.filter(
                user=user,
                entry_date__gte=week_ago,
                entry_date__lt=today,
            ).count()

            if entry_count > 0:
                title = "Votre résumé de la semaine est prêt ✨"
                message = f"Vous avez consigné {entry_count} souvenir{'s' if entry_count > 1 else ''} cette semaine. Découvrez vos tendances émotionnelles !"
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    notification_type='weekly_summary',
                    data={'entries_count': entry_count},
                )
                count += 1
        except Exception as e:
            logger.error(f"Error sending weekly summary to user {user.id}: {e}")

    logger.info(f"Weekly summaries dispatched to {count} users.")
    return count


@shared_task(name='notifications.tasks.send_monthly_memory_review')
def send_monthly_memory_review():
    """
    Monthly retrospective review notification.
    """
    today = timezone.now().date()
    users = User.objects.filter(
        is_active=True,
        preferences__monthly_review_enabled=True,
    )

    count = 0
    for user in users:
        try:
            Notification.objects.create(
                user=user,
                title="Bilan du mois MemoAi 📅",
                message="Un nouveau mois commence ! Prenez un instant pour contempler vos moments forts du mois écoulé.",
                notification_type='monthly_review',
            )
            count += 1
        except Exception as e:
            logger.error(f"Error sending monthly review to user {user.id}: {e}")

    logger.info(f"Monthly reviews dispatched to {count} users.")
    return count
