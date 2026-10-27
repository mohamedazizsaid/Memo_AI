"""
MemoAi — URL Configuration
API routes + Django Template (HTML) routes.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from common.landing_views import LandingView
from common.health_views import health_check

urlpatterns = [
    # ── Favicon fallback route ─────────────────────────────────────
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.ico', permanent=True)),

    # ── Health check (Docker / Render / CI) ────────────────────────
    path('health/', health_check, name='health_check'),

    # ── Admin Django ────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── Admin Front Office (Dashboard) ──────────────────────────────
    path('admin-panel/', include('dashboard.urls')),

    # ── REST API routes ────────────────────────────────────────────
    path('api/auth/', include('accounts.urls')),
    path('api/entries/', include('journal.urls')),
    path('api/media/', include('media_app.urls')),
    path('api/ai/', include('ai.urls')),
    path('api/people/', include('persons.urls')),
    path('api/tags/', include('tags.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/insights/', include('ai.insight_urls')),

    # ── Public landing page ────────────────────────────────────────
    path('', LandingView.as_view(), name='landing'),

    # ── Django Template (HTML) routes ──────────────────────────────
    path('journal/', include('journal.template_urls')),
    path('comptes/', include('accounts.template_urls')),
    path('personnes/', include('persons.template_urls')),
    path('tags/', include('tags.template_urls')),
    path('notifications/', include('notifications.template_urls')),
    path('insights/', include('ai.template_urls')),

    # ── Platform-wide search (navbar omnibox + results page) ───────
    path('recherche/', include('common.search_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATICFILES_DIRS[0]
        if getattr(settings, 'STATICFILES_DIRS', []) else settings.STATIC_ROOT
    )
