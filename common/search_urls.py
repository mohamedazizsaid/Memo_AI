"""MemoAi — URL routes for the platform-wide search."""

from django.urls import path

from . import search_views

app_name = 'search'

urlpatterns = [
    path('', search_views.SearchResultsView.as_view(), name='results'),
    path('api/', search_views.search_api, name='api'),
]
