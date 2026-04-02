import os
import django
from django.test import Client

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "condorcet_backend.settings")
django.setup()

client = Client()
response = client.get('/sitemap.xml')
print(f"Status Code: {response.status_code}")
print(f"Content-Type: {response.get('Content-Type')}")
print(f"Content Start: {response.content[:200]}")
