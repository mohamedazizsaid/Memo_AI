"""
MemoAi — Notifications Context Processors
Provides unread notification count to templates.
"""

from .models import Notification


def notifications_context(request):
    """Exposes unread notification count to templates."""
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
            return {
                'unread_notifications_count': unread_count,
            }
        except Exception:
            return {'unread_notifications_count': 0}
    return {'unread_notifications_count': 0}
