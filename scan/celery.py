# scan/celery.py

import os
from celery import Celery
from celery.signals import worker_process_init # Importer le signal

# Définir le module de settings de Django pour le programme 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scan.settings')

app = Celery('scan')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# --- NOUVELLE SECTION ---
@worker_process_init.connect
def on_worker_init(**kwargs):
    """
    Fonction exécutée une seule fois lorsque le processus du worker Celery démarre.
    C'est l'endroit idéal pour charger les modèles d'IA lourds.
    """
    print("Initialisation des modèles d'IA pour le worker Celery...")
    from oris.ocr_logic import initialize_models
    initialize_models()
    print("Modèles d'IA initialisés.")
# --- FIN DE LA NOUVELLE SECTION ---

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
