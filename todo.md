## Phase 1: Recherche et collecte des ressources OCR/HTR

- [x] Synthétiser les informations sur les modèles OCR open source (Tesseract, PaddleOCR, EasyOCR, DocTR, Kraken, Surya, etc.)
- [x] Synthétiser les informations sur les modèles HTR open source (TrOCR, Donut, Kraken, PyLaia, etc.)
- [x] Identifier les datasets pertinents pour l'OCR (COCO-Text, SynthText, etc.)
- [x] Identifier les datasets pertinents pour le HTR (IAM Handwriting Database, HTR-United, etc.)
- [x] Sélectionner les modèles et datasets les plus appropriés pour le projet ORIS
- [x] Préparer un résumé des technologies choisies et de leurs avantages/inconvénients



## Phase 2: Configuration de l'environnement et structure du projet

- [x] Créer la structure du projet Django ORIS
- [x] Configurer l'environnement virtuel Python
- [x] Installer les dépendances nécessaires (Django, DRF, Celery, Redis, etc.)
- [x] Créer les applications Django (accounts, organizations, ingestion, documents, ocr, validation, api)
- [x] Configurer la base de données et les modèles de base
- [x] Configurer les paramètres Django (settings.py)
- [x] Créer la structure des dossiers pour les médias et les uploads
- [x] Installer et configurer les bibliothèques OCR/HTR (PaddleOCR, Tesseract, TrOCR, etc.)


## Phase 3: Développement du backend Django et API

- [x] Créer les serializers DRF pour tous les modèles
- [x] Implémenter les vues API pour /api/batches/
- [x] Implémenter les vues API pour /api/documents/{id}/
- [x] Implémenter les vues API pour /api/pages/{id}/ocr/
- [x] Implémenter les vues API pour /api/validate/
- [x] Créer le système d'upload de fichiers
- [x] Implémenter la logique de traitement des PDF (split en pages)
- [x] Créer les webhooks et callbacks pour intégration SI
- [x] Configurer les URLs et le routage API
- [x] Tester les endpoints avec des données de test

