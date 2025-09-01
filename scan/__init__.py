# scan/__init__.py

# Importer l'application celery pour s'assurer qu'elle est chargée lorsque Django démarre.
from .celery import app as celery_app

__all__ = ('celery_app',)
