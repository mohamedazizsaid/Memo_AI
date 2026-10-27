"""
MemoAi — Dashboard Decorators
Protection des vues admin.
"""

import functools
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Décorateur pour les vues du dashboard admin (compatible fonctions et method_decorator).
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


# Alias pour compatibilité method_decorator(admin_required_method, name='dispatch')
admin_required_method = admin_required

