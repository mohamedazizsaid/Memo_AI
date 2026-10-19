"""
MemoAi — Public Landing Page View (cosmos.so style)
"""
from urllib.parse import urlparse

from django.shortcuts import render, redirect
from django.views import View


class LandingView(View):
    """Public landing page — redirect authenticated users to journal."""

    @staticmethod
    def _home_url(request):
        """Where a signed-in visitor opening "/" should land.

        A fresh entry (typed URL, bookmark, new tab) carries no referrer and
        gets the intro splash on the home page (`?welcome=1` replays it).
        A click on "Accueil" from inside the app keeps the plain URL so the
        intro does not restart on every navigation.
        """
        referer = request.META.get('HTTP_REFERER', '')
        internal = False
        if referer:
            try:
                ref_host = (urlparse(referer).hostname or '').lower()
                req_host = request.get_host().split(':')[0].lower()
                internal = bool(ref_host) and ref_host == req_host
            except ValueError:
                internal = False
        return '/journal/' if internal else '/journal/?welcome=1'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(self._home_url(request))
        return render(request, 'landing.html')
