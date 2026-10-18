"""Ad-hoc smoke test for every post-login page (temporary)."""
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
sys.path.insert(0, os.getcwd())

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver', 'localhost']

from django.test import Client  # noqa: E402
from accounts.models import User  # noqa: E402

print('--- ensure demo user ---')
u, created = User.objects.get_or_create(
    email='demo@memoai.local',
    defaults={'first_name': 'Sophie', 'last_name': 'Bernard', 'is_active': True},
)
u.is_active = True
u.set_password('DemoPass123!')
u.save()
print('demo user ok, created =', created)

client = Client()
ok = client.login(username='demo@memoai.local', password='DemoPass123!')
print('login:', ok)

paths = [
    '/',
    '/comptes/connexion/',
    '/journal/',
    '/journal/liste/',
    '/journal/nouveau/',
    '/personnes/',
    '/personnes/nouveau/',
    '/tags/',
    '/insights/',
    '/insights/?period=7',
    '/comptes/preferences/',
    '/notifications/',
]

failures = []
for p in paths:
    try:
        r = client.get(p)
        code = r.status_code
    except Exception as exc:  # noqa: BLE001
        failures.append((p, 'EXC', repr(exc)))
        continue
    status = 'OK ' if code == 200 else 'BAD'
    print(f'{status} {code}  {p}')
    if code != 200:
        failures.append((p, code, ''))

print('--- feature probes on rendered HTML ---')
home = client.get('/journal/').content.decode('utf-8', 'ignore')
checks = {
    'aurora bg': 'app-aurora' in home,
    'hero collage': 'hero-collage' in home,
    'reveal hook': 'reveal' in home,
}
for k, v in checks.items():
    print(('OK ' if v else 'MISS'), k)

prefs = client.get('/comptes/preferences/').content.decode('utf-8', 'ignore')
print(('OK ' if 'reduce_motion' in prefs else 'MISS'), 'prefs reduce_motion field')

form = client.get('/journal/nouveau/').content.decode('utf-8', 'ignore')
wchecks = {
    'wizard container': 'wizard-panel' in form,
    'step 1 panel': 'data-panel="1"' in form,
    'step 2 panel': 'data-panel="2"' in form,
    'face payload': 'face_data' in form,
    'pexels endpoint': 'api/pexels' in form,
}
for k, v in wchecks.items():
    print(('OK ' if v else 'MISS'), k)

insights = client.get('/insights/').content.decode('utf-8', 'ignore')
print(('OK ' if 'trend-chart' in insights or 'empty-insights' in insights else 'MISS'),
      'insights real/empty state')

print('--- failures ---')
print(failures or 'none')
