"""
Utilitaires pour l'API ORIS
"""

import os
import uuid
from typing import List
from django.core.files.storage import default_storage
from django.conf import settings
from documents.models import Document, Page, AuditLog
from pdf2image import convert_from_path
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def process_uploaded_file(uploaded_file, batch):
    """
    Traite un fichier uploadé et crée les objets Document et Page correspondants
    
    Args:
        uploaded_file: Fichier Django uploadé
        batch: Instance de Batch
        
    Returns:
        Document: Instance du document créé
    """
    # Déterminer le type de document
    file_extension = uploaded_file.name.lower().split('.')[-1]
    if file_extension == 'pdf':
        document_type = 'pdf'
    elif file_extension in ['jpg', 'jpeg', 'png', 'tiff', 'bmp']:
        document_type = 'image'
    else:
        document_type = 'scan'  # Par défaut
    
    # Créer le document
    document = Document.objects.create(
        batch=batch,
        original_filename=uploaded_file.name,
        file_path=uploaded_file,
        document_type=document_type,
        file_size=uploaded_file.size,
        status='uploaded'
    )
    
    try:
        # Traiter selon le type de fichier
        if document_type == 'pdf':
            pages = process_pdf_document(document)
        else:
            pages = process_image_document(document)
        
        # Mettre à jour le nombre de pages
        document.total_pages = len(pages)
        document.status = 'processing'
        document.save()
        
        logger.info(f"Document {document.id} traité avec succès: {len(pages)} pages")
        return document
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du document {document.id}: {e}")
        document.status = 'failed'
        document.save()
        raise


def process_pdf_document(document):
    """
    Traite un document PDF en extrayant chaque page comme image
    
    Args:
        document: Instance de Document
        
    Returns:
        List[Page]: Liste des pages créées
    """
    pages = []
    
    try:
        # Chemin vers le fichier PDF
        pdf_path = document.file_path.path
        
        # Conversion PDF vers images
        images = convert_from_path(pdf_path, dpi=300)
        
        for i, image in enumerate(images, 1):
            # Créer le nom de fichier pour la page
            page_filename = f"{document.id}_page_{i:03d}.png"
            page_path = os.path.join('pages', str(document.batch.id), page_filename)
            
            # Sauvegarder l'image de la page
            full_page_path = os.path.join(settings.MEDIA_ROOT, page_path)
            os.makedirs(os.path.dirname(full_page_path), exist_ok=True)
            image.save(full_page_path, 'PNG')
            
            # Créer l'objet Page
            page = Page.objects.create(
                document=document,
                page_number=i,
                image_path=page_path,
                status='extracted'
            )
            pages.append(page)
            
        return pages
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du PDF {document.id}: {e}")
        raise


def process_image_document(document):
    """
    Traite un document image (une seule page)
    
    Args:
        document: Instance de Document
        
    Returns:
        List[Page]: Liste contenant une seule page
    """
    try:
        # Ouvrir l'image
        image_path = document.file_path.path
        image = Image.open(image_path)
        
        # Créer le nom de fichier pour la page
        page_filename = f"{document.id}_page_001.png"
        page_path = os.path.join('pages', str(document.batch.id), page_filename)
        
        # Sauvegarder l'image de la page (conversion en PNG si nécessaire)
        full_page_path = os.path.join(settings.MEDIA_ROOT, page_path)
        os.makedirs(os.path.dirname(full_page_path), exist_ok=True)
        
        # Convertir en RGB si nécessaire (pour éviter les problèmes avec PNG)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        image.save(full_page_path, 'PNG')
        
        # Créer l'objet Page
        page = Page.objects.create(
            document=document,
            page_number=1,
            image_path=page_path,
            status='extracted'
        )
        
        return [page]
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'image {document.id}: {e}")
        raise


def create_audit_log(user, action, resource_type, resource_id, details=None):
    """
    Crée une entrée dans le journal d'audit
    
    Args:
        user: Utilisateur qui effectue l'action
        action: Type d'action (voir AuditLog.ACTION_CHOICES)
        resource_type: Type de ressource ('batch', 'document', 'page')
        resource_id: ID de la ressource
        details: Détails supplémentaires (dict)
    """
    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {}
        )
    except Exception as e:
        logger.error(f"Erreur lors de la création du log d'audit: {e}")


def get_file_type(filename):
    """
    Détermine le type de fichier basé sur l'extension
    
    Args:
        filename: Nom du fichier
        
    Returns:
        str: Type de fichier ('pdf', 'image', 'unknown')
    """
    extension = filename.lower().split('.')[-1]
    
    if extension == 'pdf':
        return 'pdf'
    elif extension in ['jpg', 'jpeg', 'png', 'tiff', 'tif', 'bmp', 'gif']:
        return 'image'
    else:
        return 'unknown'


def validate_file_upload(uploaded_file):
    """
    Valide un fichier uploadé
    
    Args:
        uploaded_file: Fichier Django uploadé
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Vérifier la taille du fichier (50MB max)
    max_size = 50 * 1024 * 1024  # 50MB
    if uploaded_file.size > max_size:
        return False, f"Le fichier est trop volumineux ({uploaded_file.size} bytes). Taille maximale: {max_size} bytes"
    
    # Vérifier le type de fichier
    file_type = get_file_type(uploaded_file.name)
    if file_type == 'unknown':
        return False, f"Type de fichier non supporté: {uploaded_file.name}"
    
    return True, None


def cleanup_failed_batch(batch):
    """
    Nettoie les fichiers d'un lot qui a échoué
    
    Args:
        batch: Instance de Batch
    """
    try:
        # Supprimer les fichiers des documents
        for document in batch.documents.all():
            # Supprimer le fichier principal
            if document.file_path and default_storage.exists(document.file_path.name):
                default_storage.delete(document.file_path.name)
            
            # Supprimer les images des pages
            for page in document.pages.all():
                if page.image_path and default_storage.exists(page.image_path.name):
                    default_storage.delete(page.image_path.name)
        
        # Supprimer les objets de la base de données
        batch.documents.all().delete()
        batch.delete()
        
        logger.info(f"Lot {batch.id} nettoyé avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage du lot {batch.id}: {e}")


def get_batch_progress(batch):
    """
    Calcule le progrès d'un lot
    
    Args:
        batch: Instance de Batch
        
    Returns:
        dict: Informations sur le progrès
    """
    total_pages = sum(doc.total_pages for doc in batch.documents.all())
    processed_pages = sum(doc.processed_pages for doc in batch.documents.all())
    
    progress_percentage = (processed_pages / total_pages * 100) if total_pages > 0 else 0
    
    return {
        'total_documents': batch.total_documents,
        'processed_documents': batch.processed_documents,
        'total_pages': total_pages,
        'processed_pages': processed_pages,
        'progress_percentage': round(progress_percentage, 2),
        'status': batch.status
    }

