"""
MemoAi — Tags Template Views
HTML interface for tag management.
"""

import logging
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View

from .models import Tag

logger = logging.getLogger('memoai')

COLOR_CHOICES = [
    '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f97316',
    '#eab308', '#22c55e', '#14b8a6', '#3b82f6', '#0d0d0d',
]


@method_decorator(login_required, name='dispatch')
class TagListView(View):
    def get(self, request, pk=None):
        tags = Tag.objects.filter(user=request.user)
        from django.db.models import Count
        tags = tags.annotate(entry_count=Count('entries'))
        edit_tag = None
        if pk:
            edit_tag = get_object_or_404(Tag, pk=pk, user=request.user)

        total_tags = tags.count()
        most_used_tag = tags.order_by('-entry_count').first() if total_tags else None
        total_uses = sum(t.entry_count for t in tags)

        return render(request, 'tags/list.html', {
            'tags': tags,
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

        if not name:
            messages.error(request, 'Le nom du tag est requis.')
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
