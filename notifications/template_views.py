"""
MemoAi — Notifications Template Views
"""

import logging
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View

from .models import Notification

logger = logging.getLogger('memoai')

NOTIFICATIONS_PER_PAGE = 20


@method_decorator(login_required, name='dispatch')
class NotificationListView(View):
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        paginator = Paginator(notifications, NOTIFICATIONS_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get('page', 1))
        return render(request, 'notifications/list.html', {
            'notifications': page_obj,
            'page_obj': page_obj,
            'is_paginated': paginator.num_pages > 1,
        })


@login_required
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return redirect('notifications:list')


@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'Toutes les notifications ont ete marquees comme lues.')
    return redirect('notifications:list')
