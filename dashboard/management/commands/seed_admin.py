"""
MemoAi — Seed Admin Command
Crée le compte admin par défaut : admin@memo.com / admin123
Usage: python manage.py seed_admin
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = "Crée le compte administrateur par défaut (admin@memo.com / admin123)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--email', default='admin@memo.com',
            help='Email du compte admin (défaut: admin@memo.com)'
        )
        parser.add_argument(
            '--password', default='admin123',
            help='Mot de passe du compte admin (défaut: admin123)'
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Recrée le compte admin même s\'il existe déjà'
        )

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        force = options['force']

        self.stdout.write(self.style.MIGRATE_HEADING("\n[MemoAI] Seed Admin"))
        self.stdout.write("-" * 40)

        # Verifier si le compte existe deja
        existing = User.objects.filter(email=email).first()

        if existing and not force:
            self.stdout.write(
                self.style.WARNING(f"[!] L'admin '{email}' existe deja. Utilisez --force pour recreer.")
            )
            self._ensure_preferences(existing)
            self._ensure_quota(existing)
            self.stdout.write(self.style.SUCCESS(f"[OK] Compte admin verifie : {email}"))
            return

        if existing and force:
            existing.delete()
            self.stdout.write(self.style.WARNING("    Ancien compte admin supprime."))

        # Creer le superuser
        admin = User.objects.create_superuser(
            email=email,
            password=password,
            first_name='Admin',
            last_name='MemoAI',
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Admin cree : {email}"))

        # Creer les preferences
        self._ensure_preferences(admin)
        self.stdout.write(self.style.SUCCESS("[OK] Preferences creees"))

        # Creer le quota AI
        self._ensure_quota(admin)
        self.stdout.write(self.style.SUCCESS("[OK] Quota AI initialise"))

        self.stdout.write("\n" + "-" * 40)
        self.stdout.write(self.style.SUCCESS("[DONE] Compte admin pret !"))
        self.stdout.write(f"   Email    : {email}")
        self.stdout.write(f"   Password : {password}")
        self.stdout.write(f"   URL      : /admin-panel/")
        self.stdout.write("-" * 40 + "\n")


    def _ensure_preferences(self, user):
        from accounts.models import UserPreferences
        prefs, created = UserPreferences.objects.get_or_create(user=user)
        if created:
            prefs.onboarding_completed = True
            prefs.onboarding_completed_at = timezone.now()
            prefs.language = 'fr'
            prefs.theme = 'system'
            prefs.save()

    def _ensure_quota(self, user):
        from dashboard.models import AIUsageQuota
        AIUsageQuota.objects.get_or_create(user=user)
