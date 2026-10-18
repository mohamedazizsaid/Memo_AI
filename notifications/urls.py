from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('mark-all-read/', views.mark_all_notifications_read, name='notification-mark-all-read'),
    path('<uuid:pk>/read/', views.mark_notification_read, name='notification-mark-read'),
    path('<uuid:pk>/', views.delete_notification, name='notification-delete'),
]
