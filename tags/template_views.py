"""
MemoAi — Tags Template Views
HTML interface for tag management.
"""

import logging
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View

from .models import Tag

logger = logging.getLogger('memoai')

TAGS_PER_PAGE = 18

COLOR_CHOICES = [
    '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f97316',
    '#eab308', '#22c55e', '#14b8a6', '#3b82f6', '#0d0d0d',
]


@method_decorator(login_required, name='dispatch')
class TagListView(View):
    def get(self, request, pk=None):
        from django.db.models import Count

        search = request.GET.get('q', '').strip()

        all_tags = Tag.objects.filter(user=request.user).annotate(entry_count=Count('entries'))
        total_tags = all_tags.count()
        most_used_tag = all_tags.order_by('-entry_count', 'name').first() if total_tags else None
        total_uses = sum(tag.entry_count for tag in all_tags)

        tags = all_tags
        if search:
            tags = tags.filter(name__icontains=search)
        tags = tags.order_by('name')

        paginator = Paginator(tags, TAGS_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        edit_tag = None
        if pk:
            edit_tag = get_object_or_404(Tag, pk=pk, user=request.user)

        return render(request, 'tags/list.html', {
            'tags': page_obj,
            'page_obj': page_obj,
            'is_paginated': paginator.num_pages > 1,
            'search': search,
            'edit_tag': edit_tag,
            'total_tags': total_tags,
            'most_used_tag': most_used_tag,
            'total_uses': total_uses,
            'form': {
                'name': {'value': edit_tag.name if edit_tag else ''},
                'color': {'value': edit_tag.color if edit_tag else '#6366f1'},
                'icon': {'value': edit_tag.icon if edit_tag else ''},
            },
            'color_choices': COLOR_CHOICES,
        })

    def post(self, request, pk=None):
        name = request.POST.get('name', '').strip()
        color = request.POST.get('color', '').strip() or request.POST.get('color_custom', '#6366f1').strip()
        icon = request.POST.get('icon', '').strip()

        if len(name) < 2:
            messages.error(request, 'Le nom du tag doit contenir au moins 2 caractères.')
            return redirect('tags:list')

        if pk:
            tag = get_object_or_404(Tag, pk=pk, user=request.user)
            if Tag.objects.filter(user=request.user, name=name).exclude(pk=tag.pk).exists():
                messages.error(request, f'Un tag nomme "{name}" existe deja.')
                return redirect('tags:edit', pk=tag.pk)
            tag.name = name
            tag.color = color or '#6366f1'
            tag.icon = icon
            tag.save()
            messages.success(request, f'Tag "{name}" modifie.')
        else:
            tag, created = Tag.objects.get_or_create(
                user=request.user, name=name,
                defaults={'color': color or '#6366f1', 'icon': icon}
            )
            if not created:
                messages.info(request, f'Le tag "{name}" existe deja.')
            else:
                messages.success(request, f'Tag "{name}" cree.')

        return redirect('tags:list')


@login_required
def tag_delete(request, pk):
    tag = get_object_or_404(Tag, pk=pk, user=request.user)
    name = tag.name
    tag.delete()
    messages.success(request, f'Tag "{name}" supprime.')
    return redirect('tags:list')
