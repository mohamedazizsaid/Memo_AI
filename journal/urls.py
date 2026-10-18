from django.urls import path
from . import views

urlpatterns = [
    path('', views.JournalEntryListCreateView.as_view(), name='entry-list-create'),
    path('<uuid:pk>/', views.JournalEntryDetailView.as_view(), name='entry-detail'),
    path('<uuid:pk>/analyze/', views.trigger_ai_analysis, name='entry-analyze'),
    path('stats/', views.journal_stats, name='entry-stats'),
    path('today/', views.today_entry, name='entry-today'),
    path('on-this-day/', views.on_this_day, name='entry-on-this-day'),
]
