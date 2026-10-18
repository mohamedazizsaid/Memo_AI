"""
MemoAi — Notifications Template URL Patterns
"""

from django.urls import path
from . import template_views

app_name = 'notifications'

urlpatterns = [
    path('', template_views.NotificationListView.as_view(), name='list'),
    path('<uuid:pk>/lire/', template_views.mark_read, name='mark-read'),
    path('tout-lire/', template_views.mark_all_read, name='mark-all-read'),
]
