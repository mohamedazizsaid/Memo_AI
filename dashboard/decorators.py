"""
MemoAi — Dashboard Decorators
Protection des vues admin.
"""

import functools
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Décorateur pour les vues du dashboard admin.
    - Redirige vers /comptes/connexion/ si non authentifié.
    - Redirige vers /journal/ si pas is_staff.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/comptes/connexion/?next={request.path}')
        if not request.user.is_staff:
            messages.error(request, "Accès réservé aux administrateurs.")
            return redirect('/journal/')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required_method(method):
    """
    Décorateur pour les méthodes de class-based views.
    """
    @functools.wraps(method)
    def wrapper(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/comptes/connexion/?next={request.path}')
        if not request.user.is_staff:
            messages.error(request, "Accès réservé aux administrateurs.")
            return redirect('/journal/')
        return method(self, request, *args, **kwargs)
    return wrapper
