"""
MemoAi — Journal Template URL Patterns
"""

from django.urls import path
from . import template_views

app_name = 'journal'

urlpatterns = [
    path('', template_views.HomeView.as_view(), name='home'),
    path('liste/', template_views.EntryListView.as_view(), name='list'),
    path('api/pexels/', template_views.pexels_search, name='pexels-search'),
    path('api/lieux/', template_views.place_search, name='place-search'),
    path('api/lieux/reverse/', template_views.place_reverse, name='place-reverse'),
    path('api/entree/<uuid:pk>/statut/', template_views.ai_status, name='ai-status'),
    path('nouveau/', template_views.EntryCreateView.as_view(), name='create'),
    path('<uuid:pk>/', template_views.EntryDetailView.as_view(), name='detail'),
    path('<uuid:pk>/modifier/', template_views.EntryEditView.as_view(), name='edit'),
    path('<uuid:pk>/supprimer/', template_views.entry_delete, name='delete'),
    path('<uuid:pk>/analyser/', template_views.trigger_ai_template, name='trigger-ai'),
]
