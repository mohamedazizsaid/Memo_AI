"""End-to-end test: create an entry -> real Gemini analysis + free image generation."""
import os
import sys
import time

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
sys.path.insert(0, os.getcwd())

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver', 'localhost']

from django.test import Client  # noqa: E402
from journal.models import JournalEntry  # noqa: E402

client = Client()
assert client.login(username='demo@memoai.local', password='DemoPass123!')

before = set(JournalEntry.objects.values_list('id', flat=True))

resp = client.post('/journal/nouveau/', {
    'title': 'Promenade au bord du lac',
    'content': (
        "Ce matin je suis alle marcher au bord du lac avec ma soeur. "
        "Le soleil se levait derriere les montagnes et l'air etait frais. "
        "Nous avons parle longtemps de nos projets et j'ai ressenti beaucoup de gratitude. "
        "L'apres-midi j'ai lu un livre au parc, c'etait une journee calme et joyeuse."
    ),
    'entry_date': time.strftime('%Y-%m-%d'),
    'mood': 'grateful',
    'location': 'Lac d\'Annecy',
    'word_count': '50',
})
print('POST /journal/nouveau/ ->', resp.status_code, resp.get('Location'))

after = set(JournalEntry.objects.values_list('id', flat=True))
new_ids = after - before
print('new entries:', len(new_ids))
if not new_ids:
    print('!! no entry created; aborting')
    sys.exit(1)

entry_id = list(new_ids)[0]
entry = JournalEntry.objects.get(id=entry_id)
print('entry:', entry.title, '| ai_status =', entry.ai_status)

print('waiting for the background AI pipeline ...')
deadline = time.time() + 150
seen = []
while time.time() < deadline:
    entry.refresh_from_db()
    if entry.ai_status not in seen:
        seen.append(entry.ai_status)
        print(f'  status -> {entry.ai_status} (t={int(time.time() - (deadline - 150))}s)')
    if entry.ai_status in ('completed', 'failed', 'skipped'):
        break
    time.sleep(3)

entry.refresh_from_db()
print('final ai_status:', entry.ai_status)
if entry.ai_error_message:
    print('ai_error_message:', entry.ai_error_message)

ana = getattr(entry, 'ai_analysis', None)
if ana:
    print('summary:', (ana.summary or '')[:220])
    print('keywords:', ana.keywords)
    print('sentiment:', ana.sentiment, '| score:', ana.sentiment_score)
    print('mood_insight:', (ana.mood_insight or '')[:160])
    print('image_prompt:', (ana.image_prompt or '')[:160])
    print('generated_image_url:', ana.generated_image_url)
    print('image_status:', getattr(ana, 'image_status', None))
else:
    print('no AIAnalysis row')

# Verify the media file exists on disk when an image was produced
img = (ana.generated_image_url if ana else '') or ''
if img.startswith('/media/'):
    p = os.path.join(str(settings.MEDIA_ROOT), img[len('/media/'):].replace('/', os.sep))
    print('image file exists:', os.path.exists(p), '->', p)

# Clean up so the demo account stays free of test records.
entry.delete()
print('test entry deleted:', not JournalEntry.objects.filter(id=entry_id).exists())
