"""
Configuration Celery pour ORIS
"""

import os
from celery import Celery

# Configuration de l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oris.settings')

app = Celery('oris')

# Configuration depuis les settings Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découverte automatique des tâches
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

