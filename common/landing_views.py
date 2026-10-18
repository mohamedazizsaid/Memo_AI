"""
MemoAi — Public Landing Page View (cosmos.so style)
"""
from django.shortcuts import render, redirect
from django.views import View


class LandingView(View):
    """Public landing page — redirect authenticated users to journal."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('/journal/')
        return render(request, 'landing.html')
