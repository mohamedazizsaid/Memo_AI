"""
MemoAi — Dashboard Views
Toutes les vues du panneau d'administration front-office.
"""

import json
import logging
from datetime import timedelta, date

from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.sessions.models import Session
from django.db import models as django_models
from django.db.models import Count, Sum, Avg, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from dashboard.decorators import admin_required_method
from dashboard.models import AdminLog, AIUsageQuota

logger = logging.getLogger('memoai')
User = get_user_model()


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _get_stats():
    """Stats globales de la plateforme pour la sidebar + overview."""
    return {
        'total_users': User.objects.count(),
    }


def _cloudinary_usage():
    """Tente de récupérer l'usage global Cloudinary. Retourne None si non configuré."""
    try:
        from common.cloud_media import _configure
        cl = _configure()
        import cloudinary.api
        usage = cloudinary.api.usage()
        return {
            'storage_mb': round(usage.get('storage', {}).get('usage', 0) / (1024 * 1024), 1),
            'bandwidth_mb': round(usage.get('bandwidth', {}).get('usage', 0) / (1024 * 1024), 1),
            'resources': usage.get('resources', 0),
            'transformations': usage.get('transformations', {}).get('usage', 0),
            'plan': usage.get('plan', 'Unknown'),
            'last_updated': usage.get('last_updated', ''),
        }
    except Exception as e:
        logger.warning("Cloudinary usage API unavailable: %s", e)
        return None


def _user_storage_stats():
    """Calcule le stockage par user depuis la table media_files."""
    from media_app.models import Media
    qs = (
        Media.objects.values('entry__user', 'entry__user__email',
                             'entry__user__first_name', 'entry__user__last_name')
        .annotate(
            total_bytes=Sum('file_size'),
            image_count=Count('id', filter=Q(media_type='IMAGE')),
            audio_count=Count('id', filter=Q(media_type='AUDIO')),
            video_count=Count('id', filter=Q(media_type='VIDEO')),
            ai_image_count=Count('id', filter=Q(media_type='GENERATED_IMAGE')),
        )
        .order_by('-total_bytes')
    )
    return qs


# ─────────────────────────────────────────────────────────
# Overview (homepage du dashboard)
# ─────────────────────────────────────────────────────────

@method_decorator(admin_required_method, name='dispatch')
class OverviewView(View):
    template_name = 'dashboard/overview.html'

    def get(self, request):
        now = timezone.now()
        today = now.date()
        last_7 = now - timedelta(days=7)
        last_30 = now - timedelta(days=30)

        # ── Utilisateurs ──
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        blocked_users = User.objects.filter(is_active=False).count()
        new_this_week = User.objects.filter(created_at__gte=last_7).count()
        new_this_month = User.objects.filter(created_at__gte=last_30).count()

        # ── Journal ──
        from journal.models import JournalEntry
        total_entries = JournalEntry.all_objects.count()
        active_entries = JournalEntry.objects.count()
        entries_today = JournalEntry.objects.filter(entry_date=today).count()
        entries_this_week = JournalEntry.objects.filter(entry_date__gte=last_7.date()).count()
        total_words = JournalEntry.objects.aggregate(tw=Sum('word_count'))['tw'] or 0

        # ── Médias ──
        from media_app.models import Media
        total_media = Media.objects.count()
        total_storage_bytes = Media.objects.aggregate(tb=Sum('file_size'))['tb'] or 0
        total_storage_mb = round(total_storage_bytes / (1024 * 1024), 1)

        # ── AI ──
        from ai.models import AIAnalysis
        total_ai = AIAnalysis.objects.filter(summary_status='completed').count()
        ai_today = AIAnalysis.objects.filter(
            created_at__date=today,
            summary_status='completed'
        ).count()

        # Répartition sentiments
        sentiment_qs = (
            AIAnalysis.objects.exclude(sentiment='')
            .values('sentiment').annotate(count=Count('id')).order_by('-count')
        )
        sentiments = {s['sentiment']: s['count'] for s in sentiment_qs}

        # Répartition émotions top 5
        emotion_qs = (
            AIAnalysis.objects.exclude(emotion='')
            .values('emotion').annotate(count=Count('id')).order_by('-count')[:5]
        )

        # ── Graphique inscriptions 30 jours ──
        days_labels = []
        days_signups = []
        for i in range(29, -1, -1):
            d = (now - timedelta(days=i)).date()
            days_labels.append(d.strftime('%d/%m'))
            days_signups.append(
                User.objects.filter(created_at__date=d).count()
            )

        # ── Graphique entrées 30 jours ──
        days_entries = []
        for i in range(29, -1, -1):
            d = (now - timedelta(days=i)).date()
            days_entries.append(
                JournalEntry.objects.filter(entry_date=d).count()
            )

        # ── Quota AI ──
        quotas_exceeded = AIUsageQuota.objects.filter(
            daily_count__gte=AIUsageQuota.DAILY_LIMIT,
            last_reset_date=today,
        ).count()

        # ── Logs récents ──
        recent_logs = AdminLog.objects.select_related('admin', 'target_user')[:8]

        # ── Notifications ──
        from notifications.models import Notification
        total_notifs = Notification.objects.count()
        unread_notifs = Notification.objects.filter(is_read=False).count()

        context = {
            # Users
            'total_users': total_users,
            'active_users': active_users,
            'blocked_users': blocked_users,
            'new_this_week': new_this_week,
            'new_this_month': new_this_month,
            # Journal
            'total_entries': total_entries,
            'active_entries': active_entries,
            'entries_today': entries_today,
            'entries_this_week': entries_this_week,
            'total_words': total_words,
            # Médias / Stockage
            'total_media': total_media,
            'total_storage_mb': total_storage_mb,
            # AI
            'total_ai': total_ai,
            'ai_today': ai_today,
            'sentiments': sentiments,
            'emotion_qs': list(emotion_qs),
            'quotas_exceeded': quotas_exceeded,
            # Charts (JSON)
            'chart_labels': json.dumps(days_labels),
            'chart_signups': json.dumps(days_signups),
            'chart_entries': json.dumps(days_entries),
            # Logs récents
            'recent_logs': recent_logs,
            # Notifications
            'total_notifs': total_notifs,
            'unread_notifs': unread_notifs,
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────

@method_decorator(admin_required_method, name='dispatch')
class UsersListView(View):
    template_name = 'dashboard/users_list.html'
    ITEMS_PER_PAGE = 25

    def get(self, request):
        qs = User.objects.select_related('preferences', 'ai_quota').order_by('-created_at')

        # Recherche
        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))

        # Filtres
        status = request.GET.get('status', '')
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'blocked':
            qs = qs.filter(is_active=False)
        elif status == 'staff':
            qs = qs.filter(is_staff=True)

        lang = request.GET.get('lang', '')
        if lang:
            qs = qs.filter(preferences__language=lang)

        # Pagination manuelle
        total = qs.count()
        page = max(1, int(request.GET.get('page', 1)))
        offset = (page - 1) * self.ITEMS_PER_PAGE
        users = qs[offset: offset + self.ITEMS_PER_PAGE]
        total_pages = max(1, (total + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)

        # Annotate entries count
        from journal.models import JournalEntry
        user_ids = [u.id for u in users]
        entries_by_user = dict(
            JournalEntry.objects.filter(user_id__in=user_ids)
            .values('user_id').annotate(cnt=Count('id'))
            .values_list('user_id', 'cnt')
        )

        users_data = []
        for user in users:
            quota = getattr(user, 'ai_quota', None)
            if quota:
                quota.reset_if_needed()
            users_data.append({
                'user': user,
                'entries_count': entries_by_user.get(user.id, 0),
                'quota': quota,
            })

        context = {
            'users_data': users_data,
            'total': total,
            'page': page,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'q': q,
            'status': status,
            'lang': lang,
            'page_range': range(max(1, page - 2), min(total_pages + 1, page + 3)),
            'total_users': total,
        }
        return render(request, self.template_name, context)


@method_decorator(admin_required_method, name='dispatch')
class UserDetailView(View):
    template_name = 'dashboard/user_detail.html'

    def get(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        return self._render(request, target)

    def _render(self, request, target):
        from journal.models import JournalEntry
        from media_app.models import Media
        from ai.models import AIAnalysis
        from notifications.models import Notification

        # Stats utilisateur
        entries = JournalEntry.objects.filter(user=target)
        total_entries = entries.count()
        total_words = entries.aggregate(tw=Sum('word_count'))['tw'] or 0

        media_qs = Media.objects.filter(entry__user=target)
        total_media = media_qs.count()
        total_storage_bytes = media_qs.aggregate(tb=Sum('file_size'))['tb'] or 0

        ai_analyses = AIAnalysis.objects.filter(entry__user=target, summary_status='completed')
        total_ai = ai_analyses.count()

        notifications = Notification.objects.filter(user=target).order_by('-created_at')[:10]

        # Quota AI
        quota, _ = AIUsageQuota.objects.get_or_create(user=target)
        quota.reset_if_needed()

        # Humeur la plus fréquente
        top_mood = (
            entries.exclude(mood='').values('mood')
            .annotate(cnt=Count('id')).order_by('-cnt').first()
        )

        # Émotion AI la plus fréquente
        top_emotion = (
            ai_analyses.exclude(emotion='').values('emotion')
            .annotate(cnt=Count('id')).order_by('-cnt').first()
        )

        # Dernières entrées
        recent_entries = entries.order_by('-entry_date')[:5]

        # Logs admin sur cet utilisateur
        admin_logs = AdminLog.objects.filter(
            target_user=target
        ).select_related('admin')[:10]

        # Préférences
        prefs = getattr(target, 'preferences', None)

        context = {
            'target': target,
            'prefs': prefs,
            'total_entries': total_entries,
            'total_words': total_words,
            'total_media': total_media,
            'total_storage_mb': round(total_storage_bytes / (1024 * 1024), 2),
            'total_ai': total_ai,
            'notifications': notifications,
            'quota': quota,
            'top_mood': top_mood,
            'top_emotion': top_emotion,
            'recent_entries': recent_entries,
            'admin_logs': admin_logs,
            'total_users': User.objects.count(),
        }
        return render(request, self.template_name, context)


@method_decorator(admin_required_method, name='dispatch')
class UserBlockView(View):
    """Toggle is_active pour bloquer/débloquer un utilisateur."""

    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')

        if target == request.user:
            msg = "Vous ne pouvez pas vous bloquer vous-même."
            messages.error(request, msg)
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': msg}, status=400)
            return redirect('dashboard:user_detail', user_id=user_id)

        if target.is_active:
            target.is_active = False
            target.save(update_fields=['is_active'])
            action = 'block_user'
            msg = f"Utilisateur {target.email} bloqué."
        else:
            target.is_active = True
            target.save(update_fields=['is_active'])
            action = 'unblock_user'
            msg = f"Utilisateur {target.email} débloqué."

        AdminLog.log(request.user, action, target_user=target,
                     details={'email': target.email}, request=request)
        messages.success(request, msg)

        if is_ajax:
            return JsonResponse({
                'status': 'ok',
                'is_active': target.is_active,
                'message': msg
            })

        return redirect('dashboard:user_detail', user_id=user_id)


@method_decorator(admin_required_method, name='dispatch')
class UserDeleteView(View):
    """Suppression définitive d'un utilisateur."""

    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')

        if target == request.user:
            msg = "Vous ne pouvez pas supprimer votre propre compte."
            messages.error(request, msg)
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': msg}, status=400)
            return redirect('dashboard:user_detail', user_id=user_id)

        email = target.email
        AdminLog.log(request.user, 'delete_user',
                     details={'deleted_email': email, 'deleted_id': str(target.id)},
                     request=request)
        target.delete()
        msg = f"Utilisateur {email} supprimé définitivement."
        messages.success(request, msg)

        if is_ajax:
            return JsonResponse({
                'status': 'ok',
                'message': msg,
                'redirect_url': reverse('dashboard:users_list')
            })

        return redirect('dashboard:users_list')


# ─────────────────────────────────────────────────────────
# Notifications (Centre de diffusion)
# ─────────────────────────────────────────────────────────

@method_decorator(admin_required_method, name='dispatch')
class NotificationCenterView(View):
    template_name = 'dashboard/notifications.html'

    def get(self, request):
        from notifications.models import Notification

        # Historique des 50 dernières notifications admin (type=system)
        recent = Notification.objects.select_related('user').order_by('-created_at')[:50]

        # Stats
        total_sent = Notification.objects.count()
        unread = Notification.objects.filter(is_read=False).count()
        read_rate = round((1 - unread / max(total_sent, 1)) * 100, 1)

        # Stats par type
        type_stats = (
            Notification.objects.values('notification_type')
            .annotate(cnt=Count('id')).order_by('-cnt')
        )

        context = {
            'recent_notifications': recent,
            'total_sent': total_sent,
            'unread_count': unread,
            'read_rate': read_rate,
            'type_stats': list(type_stats),
            'notification_types': [
                ('system',          'Système'),
                ('ai_complete',     'Analyse AI terminée'),
                ('memory_nostalgia','Ce jour-là'),
                ('daily_reminder',  'Rappel journalier'),
                ('weekly_summary',  'Résumé hebdo'),
                ('monthly_review',  'Bilan mensuel'),
                ('streak_milestone','Milestone streak'),
            ],
            'users': User.objects.filter(is_active=True).order_by('email'),
            'total_users': User.objects.count(),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        from notifications.models import Notification

        title = request.POST.get('title', '').strip()
        message_text = request.POST.get('message', '').strip()
        notif_type = request.POST.get('notification_type', 'system')
        target_type = request.POST.get('target_type', 'all')  # all | user | staff
        target_user_id = request.POST.get('target_user_id', '')

        if not title or not message_text:
            messages.error(request, "Le titre et le message sont obligatoires.")
            return redirect('dashboard:notifications')

        recipients = []
        if target_type == 'all':
            recipients = list(User.objects.filter(is_active=True))
        elif target_type == 'staff':
            recipients = list(User.objects.filter(is_active=True, is_staff=True))
        elif target_type == 'user' and target_user_id:
            user = User.objects.filter(pk=target_user_id).first()
            if user:
                recipients = [user]

        if not recipients:
            messages.error(request, "Aucun destinataire trouvé.")
            return redirect('dashboard:notifications')

        # Créer les notifications en bulk
        notifs = [
            Notification(
                user=u,
                title=title,
                message=message_text,
                notification_type=notif_type,
                data={'sent_by_admin': str(request.user.id)},
            )
            for u in recipients
        ]
        Notification.objects.bulk_create(notifs)

        AdminLog.log(request.user, 'send_notification',
                     details={
                         'title': title,
                         'type': notif_type,
                         'target': target_type,
                         'count': len(recipients),
                     }, request=request)

        messages.success(request, f"✓ Notification envoyée à {len(recipients)} utilisateur(s).")
        return redirect('dashboard:notifications')


# ─────────────────────────────────────────────────────────
# AI Usage / Quotas
# ─────────────────────────────────────────────────────────

@method_decorator(admin_required_method, name='dispatch')
class AIUsageView(View):
    template_name = 'dashboard/ai_usage.html'

    def get(self, request):
        today = timezone.now().date()

        # S'assurer que tous les users ont un quota
        users_without_quota = User.objects.exclude(ai_quota__isnull=False)
        for u in users_without_quota:
            AIUsageQuota.objects.get_or_create(user=u)

        # Quotas avec info user
        quotas = (
            AIUsageQuota.objects.select_related('user')
            .order_by('-daily_count', '-total_analyses')
        )

        # Reset les quotas du jour si nécessaire
        for q in quotas:
            q.reset_if_needed()

        # Stats globales
        total_today = sum(q.daily_count for q in quotas if q.last_reset_date == today)
        quota_exceeded = sum(1 for q in quotas if q.last_reset_date == today and q.daily_count >= AIUsageQuota.DAILY_LIMIT)
        total_all_time = AIUsageQuota.objects.aggregate(t=Sum('total_analyses'))['t'] or 0

        # Graphique 7 derniers jours (depuis AIAnalysis.created_at)
        from ai.models import AIAnalysis
        days_labels = []
        days_ai = []
        for i in range(6, -1, -1):
            d = (timezone.now() - timedelta(days=i)).date()
            days_labels.append(d.strftime('%d/%m'))
            days_ai.append(AIAnalysis.objects.filter(
                summary_status='completed', created_at__date=d).count())

        # Recherche
        q = request.GET.get('q', '').strip()
        if q:
            quotas = quotas.filter(
                Q(user__email__icontains=q) | Q(user__first_name__icontains=q)
            )

        context = {
            'quotas': quotas,
            'daily_limit': AIUsageQuota.DAILY_LIMIT,
            'total_today': total_today,
            'quota_exceeded': quota_exceeded,
            'total_all_time': total_all_time,
            'chart_labels': json.dumps(days_labels),
            'chart_ai': json.dumps(days_ai),
            'q': q,
            'total_users': User.objects.count(),
        }
        return render(request, self.template_name, context)


@method_decorator(admin_required_method, name='dispatch')
class AIQuotaResetView(View):
    """Reset manuel du quota AI d'un utilisateur."""

    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        quota, _ = AIUsageQuota.objects.get_or_create(user=target)
        quota.reset_daily()

        AdminLog.log(request.user, 'reset_quota', target_user=target,
                     details={'email': target.email}, request=request)
        messages.success(request, f"Quota AI réinitialisé pour {target.email}.")

        next_url = request.POST.get('next', 'dashboard:ai_usage')
        if next_url.startswith('/'):
            return redirect(next_url)
        return redirect('dashboard:ai_usage')


# ─────────────────────────────────────────────────────────
# Storage Cloudinary
# ─────────────────────────────────────────────────────────

@method_decorator(admin_required_method, name='dispatch')
class StorageView(View):
    template_name = 'dashboard/storage.html'

    def get(self, request):
        # Usage global Cloudinary
        cloudinary_usage = _cloudinary_usage()

        # Usage par user depuis DB
        user_storage = list(_user_storage_stats())

        # Totaux DB
        from media_app.models import Media
        total_images = Media.objects.filter(media_type='IMAGE').count()
        total_audio = Media.objects.filter(media_type='AUDIO').count()
        total_video = Media.objects.filter(media_type='VIDEO').count()
        total_ai_img = Media.objects.filter(media_type='GENERATED_IMAGE').count()
        total_bytes = Media.objects.aggregate(tb=Sum('file_size'))['tb'] or 0

        # Répartition par type (bytes)
        type_bytes = {}
        for mt, label in [('IMAGE', 'Images'), ('AUDIO', 'Audio'), ('VIDEO', 'Vidéo'), ('GENERATED_IMAGE', 'IA')]:
            b = Media.objects.filter(media_type=mt).aggregate(s=Sum('file_size'))['s'] or 0
            type_bytes[label] = b

        # Enrichir user_storage avec noms
        user_ids = [row['entry__user'] for row in user_storage]
        users_map = {str(u.id): u for u in User.objects.filter(id__in=user_ids)}

        enriched = []
        for row in user_storage[:20]:  # top 20
            uid = str(row['entry__user'])
            u = users_map.get(uid)
            enriched.append({
                'user': u,
                'email': row['entry__user__email'],
                'total_mb': round((row['total_bytes'] or 0) / (1024 * 1024), 2),
                'total_bytes': row['total_bytes'] or 0,
                'image_count': row['image_count'],
                'audio_count': row['audio_count'],
                'video_count': row['video_count'],
                'ai_image_count': row['ai_image_count'],
            })

        context = {
            'cloudinary_usage': cloudinary_usage,
            'user_storage': enriched,
            'total_images': total_images,
            'total_audio': total_audio,
            'total_video': total_video,
            'total_ai_img': total_ai_img,
            'total_storage_mb': round(total_bytes / (1024 * 1024), 2),
            'type_bytes': {k: round(v / (1024 * 1024), 2) for k, v in type_bytes.items()},
            'chart_labels': json.dumps(list(type_bytes.keys())),
            'chart_values': json.dumps([round(v / (1024 * 1024), 2) for v in type_bytes.values()]),
            'total_users': User.objects.count(),
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────
# Logs
# ─────────────────────────────────────────────────────────

@method_decorator(admin_required_method, name='dispatch')
class LogsView(View):
    template_name = 'dashboard/logs.html'
    ITEMS_PER_PAGE = 50

    def get(self, request):
        qs = AdminLog.objects.select_related('admin', 'target_user').order_by('-created_at')

        # Filtres
        action_filter = request.GET.get('action', '')
        if action_filter:
            qs = qs.filter(action=action_filter)

        admin_filter = request.GET.get('admin', '')
        if admin_filter:
            qs = qs.filter(admin__email__icontains=admin_filter)

        date_from = request.GET.get('date_from', '')
        if date_from:
            try:
                from datetime import datetime
                dt = datetime.strptime(date_from, '%Y-%m-%d')
                qs = qs.filter(created_at__date__gte=dt.date())
            except ValueError:
                pass

        # Pagination
        total = qs.count()
        try:
            page = max(1, int(request.GET.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            per_page = int(request.GET.get('per_page', 10))
            if per_page not in (10, 25, 50, 100):
                per_page = 10
        except (ValueError, TypeError):
            per_page = 10

        total_pages = max(1, (total + per_page - 1) // per_page)
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page
        logs = qs[offset: offset + per_page]

        # Couleurs des actions
        action_colors = {
            'block_user':       'danger',
            'delete_user':      'danger',
            'unblock_user':     'success',
            'send_notification':'info',
            'reset_quota':      'warning',
            'admin_login':      'info',
            'view_user':        'neutral',
            'revoke_session':   'warning',
        }

        context = {
            'logs': logs,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'page_range': range(max(1, page - 2), min(total_pages + 1, page + 3)),
            'action_filter': action_filter,
            'admin_filter': admin_filter,
            'date_from': date_from,
            'action_choices': AdminLog.ACTION_CHOICES,
            'action_colors': action_colors,
            'total_users': User.objects.count(),
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────
# API JSON (actions AJAX)
# ─────────────────────────────────────────────────────────

@method_decorator(admin_required_method, name='dispatch')
class UserSessionsView(View):
    """Sessions actives approximatives (JWT blacklist info)."""

    def get(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        # JWT n'expose pas les sessions directement — on retourne les infos disponibles
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
        outstanding = OutstandingToken.objects.filter(user=target).select_related('blacklistedtoken')
        sessions = []
        for token in outstanding:
            is_blacklisted = hasattr(token, 'blacklistedtoken')
            if not is_blacklisted and token.expires_at and token.expires_at > timezone.now():
                sessions.append({
                    'jti': token.jti,
                    'created_at': token.created_at.isoformat(),
                    'expires_at': token.expires_at.isoformat(),
                    'active': True,
                })

        return JsonResponse({'sessions': sessions, 'count': len(sessions)})


@method_decorator(admin_required_method, name='dispatch')
class RevokeSessionsView(View):
    """Révoque toutes les sessions actives d'un user (blacklist tous ses tokens)."""

    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            tokens = OutstandingToken.objects.filter(user=target)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)

            AdminLog.log(request.user, 'revoke_session', target_user=target,
                         details={'email': target.email, 'tokens_revoked': tokens.count()},
                         request=request)
            messages.success(request, f"Toutes les sessions de {target.email} ont été révoquées.")
        except Exception as e:
            logger.error("Failed to revoke sessions for %s: %s", target.email, e)
            messages.error(request, "Erreur lors de la révocation des sessions.")

        return redirect('dashboard:user_detail', user_id=user_id)
