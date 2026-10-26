import os
import django
import re

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from journal.models import JournalEntry
from tags.models import Tag

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

for t in Tag.objects.all():
    matches = EMOJI_PATTERN.findall(t.name)
    if matches:
        print(f"Tag {t.id}: '{t.name}' -> {matches}")

for e in JournalEntry.objects.all():
    matches_title = EMOJI_PATTERN.findall(e.title or '')
    if matches_title:
        print(f"Entry {e.id} title: '{e.title}' -> {matches_title}")
