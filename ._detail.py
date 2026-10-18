"""Verify the entry-detail AI processing panel + the ai-status polling endpoint."""
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
sys.path.insert(0, os.getcwd())

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver', 'localhost']

from django.test import Client  # noqa: E402
from django.utils import timezone  # noqa: E402
from accounts.models import User  # noqa: E402
from journal.models import JournalEntry  # noqa: E402

u = User.objects.get(email='demo@memoai.local')
client = Client()
assert client.login(username='demo@memoai.local', password='DemoPass123!')

# Simulate an entry whose analysis is still running (no network calls).
entry = JournalEntry.objects.create(
    user=u, title='Analyse en cours', content='Contenu de test.',
    entry_date=timezone.now().date(), ai_status='processing',
)
print('entry id:', entry.pk, '| ai_status:', entry.ai_status)

resp = client.get(f'/journal/{entry.pk}/')
html = resp.content.decode('utf-8', 'ignore')
print('detail status:', resp.status_code)
checks = {
    'processing panel': 'ai-processing' in html,
    'status url attribute': f'/journal/{entry.pk}/statut/' in html,
    'poll data-status': 'data-status="processing"' in html,
}
for k, v in checks.items():
    print(('OK ' if v else 'MISS'), k)

r = client.get(f'/journal/{entry.pk}/statut/',
               HTTP_X_REQUESTED_WITH='XMLHttpRequest')
print('ai-status endpoint:', r.status_code, r.get('Content-Type'))
print('payload:', r.json() if r.status_code == 200 else r.content[:200])

entry.delete()
print('cleaned up:', not JournalEntry.objects.filter(pk=entry.pk).exists())
print('demo entries now:', JournalEntry.objects.filter(user=u).count())
