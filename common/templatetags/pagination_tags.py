"""
MemoAi — Pagination helpers shared by every server-rendered list.

``page_url`` keeps the current query string (filters, search…) while changing
only the requested page, and ``page_window`` builds the compact page-number
strip (1 … 4 5 6 … 12).
"""

from django import template
from django.http import QueryDict

register = template.Library()


@register.simple_tag(takes_context=True)
def page_url(context, page, param='page', anchor=''):
    """Return the current URL with ``param`` set to ``page`` (+ optional hash)."""
    request = context.get('request')
    params = request.GET.copy() if request is not None else QueryDict('', mutable=True)

    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1

    if page <= 1:
        params.pop(param, None)
    else:
        params[param] = str(page)

    query = params.urlencode()
    url = ('?' + query) if query else ''
    if anchor:
        url += '#' + anchor.lstrip('#')
    return url or '?'


@register.filter
def page_window(page_obj, radius=2):
    """Return page numbers around the current one, with ``None`` as ellipsis."""
    try:
        current = int(page_obj.number)
        total = int(page_obj.paginator.num_pages)
    except (AttributeError, TypeError, ValueError):
        return []

    if total <= 1:
        return [1]

    try:
        radius = max(0, int(radius))
    except (TypeError, ValueError):
        radius = 2

    start = max(2, current - radius)
    end = min(total - 1, current + radius)

    pages = [1]
    if start > 2:
        pages.append(None)
    pages.extend(range(start, end + 1))
    if end < total - 1:
        pages.append(None)
    pages.append(total)
    return pages
