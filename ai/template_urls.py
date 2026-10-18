"""
MemoAi — AI Template URL Patterns
Mounted at /insights/ in config/urls.py so path here is empty.
"""
from django.urls import path
from . import template_views

app_name = 'ai'

urlpatterns = [
    path('', template_views.InsightsView.as_view(), name='insights'),
]
