# oris/tasks.py

import logging
from celery import shared_task
from django.conf import settings
from django.db import transaction

# Importer les modèles nécessaires
from .models import Batch, Document, Page, OCRResult

# Importer les deux types de processeurs OCR
from .ocr_logic import OCRProcessor, MockOCRProcessor

# Configuration du logger
logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_batch_task(self, batch_id: str):
    """
    Tâche Celery principale pour traiter un lot complet.
    Cette tâche ne fait que lancer des sous-tâches pour chaque document.
    """
    try:
        batch = Batch.objects.get(id=batch_id)
        
        # Mettre à jour le statut du lot pour indiquer le début du traitement
        batch.status = Batch.Status.PROCESSING
        batch.save(update_fields=['status'])
        
        logger.info(f"Début du traitement du lot {batch.id}...")

        documents = batch.documents.all()
        total_docs = documents.count()

        for i, document in enumerate(documents):
            # Mettre à jour l'état de la tâche parente pour le suivi de la progression
            self.update_state(
                state='PROGRESS', 
                meta={'current': i + 1, 'total': total_docs, 'doc_id': str(document.id)}
            )
            
            try:
                # Lancer une sous-tâche pour chaque document
                process_document_task.delay(document.id)
            except Exception as e:
                logger.error(f"Erreur lors du lancement de la tâche pour le document {document.id}: {e}")
                document.status = Document.Status.FAILED
                document.save(update_fields=['status'])

        logger.info(f"Toutes les tâches de document pour le lot {batch.id} ont été lancées.")
        return {'status': 'SUCCESS', 'batch_id': str(batch.id)}

    except Batch.DoesNotExist:
        logger.error(f"Le lot avec l'ID {batch_id} n'a pas été trouvé.")
        return {'status': 'FAILED', 'error': 'Batch not found'}
    except Exception as e:
        logger.error(f"Erreur majeure lors du traitement du lot {batch_id}: {e}", exc_info=True)
        if 'batch' in locals():
            batch.status = Batch.Status.FAILED
            batch.save(update_fields=['status'])
        return {'status': 'FAILED', 'error': str(e)}


@shared_task
def process_document_task(document_id: str):
    """
    Tâche Celery pour traiter un seul document (ses pages).
    Utilise le processeur réel ou une maquette selon le réglage dans settings.py.
    """
    try:
        # Utiliser transaction.atomic pour s'assurer que toutes les modifications
        # de la base de données pour ce document sont appliquées en une seule fois.
        with transaction.atomic():
            document = Document.objects.select_for_update().get(id=document_id)
            
            document.status = Document.Status.PROCESSING
            document.save(update_fields=['status'])
            logger.info(f"Traitement du document {document.id}...")

            # --- CHOIX DU PROCESSEUR OCR ---
            if getattr(settings, 'DEV_MODE_MOCK_OCR', False):
                # En mode développement, utiliser le processeur léger qui simule les résultats
                ocr_processor = MockOCRProcessor()
            else:
                # En production (ou pour des tests réels), utiliser le vrai processeur
                ocr_processor = OCRProcessor()
            # --- FIN DU CHOIX ---

            pages_succes = 0
            for page in document.pages.all().order_by('page_number'):
                page.status = Page.Status.OCR_PROCESSING
                page.save(update_fields=['status'])
                
                try:
                    # Le chemin de l'image est nécessaire pour le traitement
                    if not page.image_path:
                        raise FileNotFoundError(f"Le chemin de l'image pour la page {page.id} est manquant.")
                    
                    image_path = page.image_path.path
                    ocr_result_data = ocr_processor.process_image(image_path)

                    # Sauvegarde du résultat OCR
                    OCRResult.objects.create(
                        page=page,
                        engine=ocr_result_data.get('engine', 'unknown'),
                        raw_text=ocr_result_data.get('text', ''),
                        confidence_score=ocr_result_data.get('confidence', 0.0),
                        processing_time=ocr_result_data.get('processing_time', 0.0),
                        bounding_boxes=ocr_result_data.get('bounding_boxes', {}) 
                    )
                    
                    page.status = Page.Status.VALIDATION_PENDING
                    page.save(update_fields=['status'])
                    pages_succes += 1

                except Exception as e:
                    logger.error(f"Erreur OCR sur la page {page.id}: {e}", exc_info=True)
                    page.status = Page.Status.FAILED
                    page.save(update_fields=['status'])

            # Mettre à jour le statut final du document
            document.processed_pages = pages_succes
            if pages_succes == document.total_pages:
                document.status = Document.Status.OCR_COMPLETED
            else:
                # Si au moins une page a échoué, le document est en erreur
                document.status = Document.Status.FAILED
            document.save(update_fields=['status', 'processed_pages'])
            
            # Mettre à jour le statut du lot parent
            batch = document.batch
            processed_docs_count = batch.documents.filter(
                status__in=[Document.Status.OCR_COMPLETED, Document.Status.FAILED]
            ).count()
            
            batch.processed_documents = processed_docs_count
            
            # Si tous les documents du lot sont traités, marquer le lot comme terminé
            if processed_docs_count >= batch.total_documents:
                batch.status = Batch.Status.COMPLETED
            
            batch.save(update_fields=['processed_documents', 'status'])

            logger.info(f"Document {document.id} traité. {pages_succes}/{document.total_pages} pages réussies.")

    except Document.DoesNotExist:
        logger.error(f"Le document avec l'ID {document_id} n'a pas été trouvé.")
    except Exception as e:
        logger.error(f"Erreur majeure lors du traitement du document {document_id}: {e}", exc_info=True)
        # Tenter de marquer le document comme échoué même en cas d'erreur majeure
        try:
            doc_to_fail = Document.objects.get(id=document_id)
            doc_to_fail.status = Document.Status.FAILED
            doc_to_fail.save(update_fields=['status'])
        except Document.DoesNotExist:
            pass # Le document n'existe pas, rien à faire
