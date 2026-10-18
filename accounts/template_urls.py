"""
MemoAi — Accounts Template URL Patterns
"""

from django.urls import path
from . import template_views

app_name = 'accounts'

urlpatterns = [
    path('connexion/', template_views.TemplateLoginView.as_view(), name='login'),
    path('inscription/', template_views.TemplateRegisterView.as_view(), name='register'),
    path('deconnexion/', template_views.TemplateLogoutView.as_view(), name='logout'),
    path('profil/', template_views.TemplateProfileView.as_view(), name='profile'),
    path('preferences/', template_views.TemplatePreferencesView.as_view(), name='preferences'),
    path('mot-de-passe/changer/', template_views.TemplatePasswordChangeView.as_view(), name='password-change'),
    path('notifications/', template_views.redirect_to_prefs_notifications, name='preferences-notifications'),
    path('mot-de-passe/reinitialiser/', template_views.TemplatePasswordResetView.as_view(), name='password-reset'),
    path('supprimer/', template_views.template_delete_account, name='delete-account'),
    path('changer-langue/', template_views.set_language_view, name='set-language'),
]
