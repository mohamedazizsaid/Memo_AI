"""
MemoAi — Dashboard Models
AdminLog: audit trail de toutes les actions admin.
AIUsageQuota: rate limit 3 analyses AI / jour / user.
"""

import uuid
from django.db import models
from django.utils import timezone


class AdminLog(models.Model):
    """
    Audit trail de toutes les actions effectuées par les admins.
    """
    ACTION_CHOICES = [
        ('block_user',          'Bloquer utilisateur'),
        ('unblock_user',        'Débloquer utilisateur'),
        ('delete_user',         'Supprimer utilisateur'),
        ('send_notification',   'Envoyer notification'),
        ('reset_quota',         'Réinitialiser quota AI'),
        ('admin_login',         'Connexion admin'),
        ('view_user',           'Consulter profil utilisateur'),
        ('revoke_session',      'Révoquer session'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_actions',
        db_index=True,
    )
    target_user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_log_entries',
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'dashboard_admin_logs'
        verbose_name = 'Admin Log'
        verbose_name_plural = 'Admin Logs'
        ordering = ['-created_at']

    def __str__(self):
        admin_email = self.admin.email if self.admin else 'unknown'
        return f"AdminLog({admin_email} → {self.action})"

    @classmethod
    def log(cls, admin, action, target_user=None, details=None, request=None):
        """Helper pour créer un log facilement depuis les vues."""
        ip = None
        if request:
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')
        return cls.objects.create(
            admin=admin,
            action=action,
            target_user=target_user,
            details=details or {},
            ip_address=ip,
        )


class AIUsageQuota(models.Model):
    """
    Rate limit : 3 analyses AI maximum par jour par utilisateur.
    Réinitialisation automatique chaque jour à minuit (UTC).
    """
    DAILY_LIMIT = 3

    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='ai_quota',
        db_index=True,
    )
    daily_count = models.IntegerField(default=0)
    last_reset_date = models.DateField(default=timezone.localdate)
    total_analyses = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dashboard_ai_usage_quota'
        verbose_name = 'AI Usage Quota'
        verbose_name_plural = 'AI Usage Quotas'

    def __str__(self):
        return f"AIQuota({self.user.email}: {self.daily_count}/{self.DAILY_LIMIT})"

    def reset_if_needed(self):
        """Réinitialise le compteur journalier si le jour a changé."""
        today = timezone.now().date()
        if self.last_reset_date < today:
            self.daily_count = 0
            self.last_reset_date = today
            self.save(update_fields=['daily_count', 'last_reset_date'])

    def can_analyze(self) -> bool:
        """Retourne True si l'utilisateur peut encore faire une analyse aujourd'hui."""
        self.reset_if_needed()
        return self.daily_count < self.DAILY_LIMIT

    def increment(self):
        """Incrémente le compteur journalier et le total."""
        self.reset_if_needed()
        self.daily_count += 1
        self.total_analyses += 1
        self.save(update_fields=['daily_count', 'total_analyses'])

    def reset_daily(self):
        """Réinitialisation manuelle (par un admin)."""
        self.daily_count = 0
        self.last_reset_date = timezone.now().date()
        self.save(update_fields=['daily_count', 'last_reset_date'])

    @property
    def remaining(self):
        self.reset_if_needed()
        return max(0, self.DAILY_LIMIT - self.daily_count)

    @property
    def percent_used(self):
        self.reset_if_needed()
        return min(100, int((self.daily_count / self.DAILY_LIMIT) * 100))
