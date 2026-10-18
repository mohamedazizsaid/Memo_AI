"""
MemoAi — Persons Template URL Patterns
"""

from django.urls import path
from . import template_views

app_name = 'persons'

urlpatterns = [
    path('', template_views.PersonListView.as_view(), name='list'),
    path('nouveau/', template_views.PersonCreateView.as_view(), name='create'),
    path('<uuid:pk>/', template_views.PersonDetailView.as_view(), name='detail'),
    path('<uuid:pk>/modifier/', template_views.PersonEditView.as_view(), name='edit'),
    path('<uuid:pk>/supprimer/', template_views.person_delete, name='delete'),
]
