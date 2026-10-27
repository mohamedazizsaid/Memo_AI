"""
MemoAi — Dashboard URL Patterns
Préfixe: /admin-panel/
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # ── Overview ────────────────────────────────────────────────
    path('', views.OverviewView.as_view(), name='overview'),

    # ── Users ───────────────────────────────────────────────────
    path('users/', views.UsersListView.as_view(), name='users_list'),
    path('users/<uuid:user_id>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<uuid:user_id>/block/', views.UserBlockView.as_view(), name='user_block'),
    path('users/<uuid:user_id>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('users/<uuid:user_id>/sessions/', views.UserSessionsView.as_view(), name='user_sessions'),
    path('users/<uuid:user_id>/revoke-sessions/', views.RevokeSessionsView.as_view(), name='revoke_sessions'),

    # ── Notifications ────────────────────────────────────────────
    path('notifications/', views.NotificationCenterView.as_view(), name='notifications'),

    # ── AI Quotas ────────────────────────────────────────────────
    path('ai-usage/', views.AIUsageView.as_view(), name='ai_usage'),
    path('ai-usage/<uuid:user_id>/reset/', views.AIQuotaResetView.as_view(), name='ai_quota_reset'),

    # ── Storage ──────────────────────────────────────────────────
    path('storage/', views.StorageView.as_view(), name='storage'),

    # ── Logs ─────────────────────────────────────────────────────
    path('logs/', views.LogsView.as_view(), name='logs'),
]
