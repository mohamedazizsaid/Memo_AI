"""
MemoAi — Notifications Context Processors
Provides the unread count and a small recent list to templates (nav panel).
"""

from .models import Notification


def notifications_context(request):
    """Exposes unread notification count + recent notifications to templates."""
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            qs = Notification.objects.filter(user=request.user)
            return {
                'unread_notifications_count': qs.filter(is_read=False).count(),
                'recent_notifications': list(qs[:6]),
            }
        except Exception:
            return {'unread_notifications_count': 0, 'recent_notifications': []}
    return {'unread_notifications_count': 0, 'recent_notifications': []}
