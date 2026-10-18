"""
MemoAi — Accounts URL Patterns
Authentication and user management API routes.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('login/', views.LoginView.as_view(), name='auth-login'),
    path('logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),

    # Profile & Preferences
    path('profile/', views.ProfileView.as_view(), name='auth-profile'),
    path('me/', views.ProfileView.as_view(), name='auth-me'),
    path('preferences/', views.PreferencesView.as_view(), name='auth-preferences'),


    # Password management
    path('password/change/', views.ChangePasswordView.as_view(), name='auth-password-change'),
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='auth-password-reset'),
    path('password/reset/confirm/', views.PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),

    # Face recognition consent
    path('face-recognition/consent/', views.grant_face_recognition_consent, name='auth-face-consent-grant'),
    path('face-recognition/revoke/', views.revoke_face_recognition_consent, name='auth-face-consent-revoke'),

    # Account management
    path('delete/', views.delete_account, name='auth-delete-account'),
]
