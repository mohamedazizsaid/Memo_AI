"""
MemoAi — Tags Template URL Patterns
"""

from django.urls import path
from . import template_views

app_name = 'tags'

urlpatterns = [
    path('', template_views.TagListView.as_view(), name='list'),
    path('nouveau/', template_views.TagListView.as_view(), name='create'),
    path('<uuid:pk>/modifier/', template_views.TagListView.as_view(), name='edit'),
    path('<uuid:pk>/supprimer/', template_views.tag_delete, name='delete'),
]
