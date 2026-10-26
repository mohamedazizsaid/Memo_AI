import os
import django
import re

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from journal.models import JournalEntry
from ai.models import AIAnalysis

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "]+",
    flags=re.UNICODE
)

print("Checking JournalEntry moods & emotions in DB:")
for e in JournalEntry.objects.all():
    print(f"Entry {e.id}: mood='{e.mood}' title='{e.title}'")
    m_matches = EMOJI_PATTERN.findall(e.mood or '')
    if m_matches:
        print(f"  FOUND EMOJI IN MOOD FIELD: {m_matches}")

for a in AIAnalysis.objects.all():
    if hasattr(a, 'emotion'):
        print(f"Analysis {a.id}: emotion='{a.emotion}'")
        e_matches = EMOJI_PATTERN.findall(a.emotion or '')
        if e_matches:
            print(f"  FOUND EMOJI IN EMOTION FIELD: {e_matches}")
