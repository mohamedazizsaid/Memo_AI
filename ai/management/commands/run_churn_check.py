"""
MemoAi — Management Command: Run Churn Check & Re-engagement
============================================================
Exécute manuellement l'inférence du modèle de churn et envoie les emails
d'encouragement aux utilisateurs inactifs ou en risque d'abandon.

Usage :
    python manage.py run_churn_check --dry-run
    python manage.py run_churn_check --threshold 0.50
"""

from django.core.management.base import BaseCommand
from ai.tasks import check_churn_risk_and_reengage_users
from ai.ml.churn_service import get_churn_predictor
from accounts.models import User


class Command(BaseCommand):
    help = "Analyse le churn des utilisateurs et declenche les emails d'encouragement"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Effectue les predictions sans envoyer d\'emails ni creer de notifications',
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.55,
            help='Seuil de probabilite de churn a partir duquel contacter l\'utilisateur (defaut: 0.55)',
        )
        parser.add_argument(
            '--show-all',
            action='store_true',
            help='Affiche le score et les raisons pour chaque utilisateur',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        threshold = options['threshold']
        show_all = options['show_all']

        self.stdout.write(self.style.NOTICE("=== Lancement de l'analyse Churn (MemoAi) ==="))
        predictor = get_churn_predictor()

        if show_all:
            self.stdout.write("\nDiagnostic detaille de tous les utilisateurs :")
            users = User.objects.filter(is_active=True, is_staff=False)
            for u in users:
                res = predictor.predict_user(u)
                color = self.style.ERROR if res['is_churn'] else self.style.SUCCESS
                self.stdout.write(color(
                    f" - {u.email:<30} | Prob: {res['churn_probability']*100:5.1f}% | Risque: {res['risk_level']} | Raisons: {', '.join(res['reasons']) or 'Actif'}"
                ))
            self.stdout.write("")

        # Lancer la tâche
        summary = check_churn_risk_and_reengage_users(dry_run=dry_run, threshold=threshold)

        self.stdout.write(self.style.SUCCESS(
            f"\nScan termine avec succes !\n"
            f" - Utilisateurs verifies : {summary['total_checked']}\n"
            f" - Utilisateurs a risque   : {summary['at_risk_count']}\n"
            f" - Reengagements envoyes   : {summary['reengaged_count']} (dry_run={dry_run})\n"
        ))
