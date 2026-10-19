"""
MemoAi — Public Landing Page View (cosmos.so style)
"""
from django.shortcuts import render, redirect
from django.views import View


class LandingView(View):
    """Public landing page — redirect authenticated users to journal.

    Signed-in visitors always land on the intro splash: the home page plays
    it whenever `?welcome=1` is present, which is exactly the "splash first,
    then home" entrance. Anonymous visitors stay on the public landing,
    where the splash is enabled too (see `{% block splash_policy %}`).
    """

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('/journal/?welcome=1')
        return render(request, 'landing.html')
