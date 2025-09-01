# oris/utils.py (Nouvelle version avec PyMuPDF, sans Poppler)

import os
import uuid
import logging
from django.conf import settings
from .models import Document, Page, Batch
from PIL import Image
import fitz  # C'est l'import pour PyMuPDF

logger = logging.getLogger(__name__)

def process_uploaded_file(uploaded_file, batch: Batch) -> Document:
    """
    Crée un Document et ses Pages à partir d'un fichier uploadé.
    Utilise PyMuPDF pour les PDF, éliminant le besoin de Poppler.
    """
    logger.info(f"Traitement du fichier : {uploaded_file.name}")
    
    file_extension = uploaded_file.name.lower().split('.')[-1]
    doc_type_map = {'pdf': 'pdf', 'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'tiff': 'image'}
    document_type = doc_type_map.get(file_extension, 'scan')

    # Créer l'objet Document en premier
    document = Document.objects.create(
        batch=batch,
        original_filename=uploaded_file.name,
        document_type=document_type,
        file_size=uploaded_file.size,
        status=Document.Status.UPLOADED
    )
    
    # Sauvegarder le fichier physique associé au document
    # Utiliser un nom de fichier unique pour éviter les conflits
    unique_filename = f"{document.id}_{uploaded_file.name}"
    document.file_path.save(unique_filename, uploaded_file)
    logger.info(f"Document créé en base de données avec ID : {document.id}")

    try:
        if document_type == 'pdf':
            page_paths_data = _extract_pages_from_pdf_with_pymupdf(document)
        else:
            page_paths_data = _process_image_document(document)
        
        # Créer les objets Page en base de données
        for i, page_data in enumerate(page_paths_data, 1):
            Page.objects.create(
                document=document,
                page_number=i,
                image_path=page_data['path'],
                width=page_data['width'],
                height=page_data['height'],
                status=Page.Status.EXTRACTED
            )

        document.total_pages = len(page_paths_data)
        document.save()
        logger.info(f"Document {document.id} préparé avec succès ({len(page_paths_data)} pages).")
        return document

    except Exception as e:
        logger.error(f"Erreur lors de la préparation du document {document.id}: {e}", exc_info=True)
        document.status = Document.Status.FAILED
        document.save()
        raise

def _extract_pages_from_pdf_with_pymupdf(document: Document) -> list:
    """
    Extrait les pages d'un PDF en utilisant PyMuPDF (fitz).
    """
    pdf_path = document.file_path.path
    logger.info(f"Extraction des pages du PDF '{pdf_path}' avec PyMuPDF.")

    page_paths_data = []
    output_dir = os.path.join(settings.MEDIA_ROOT, 'pages', str(document.batch.id))
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Ouvrir le document PDF
        pdf_document = fitz.open(pdf_path)
        
        # Itérer sur chaque page
        for page_number in range(len(pdf_document)):
            page = pdf_document.load_page(page_number)
            
            # Rendre la page en image (pixmap)
            # dpi=300 pour une haute qualité, nécessaire pour un bon OCR
            pix = page.get_pixmap(dpi=300)
            
            # Créer une image PIL à partir du pixmap
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Sauvegarder l'image
            page_filename = f"{document.id}_page_{page_number + 1:03d}.png"
            absolute_page_path = os.path.join(output_dir, page_filename)
            img.save(absolute_page_path, 'PNG')
            
            # Chemin relatif pour le modèle Django
            relative_page_path = os.path.join('pages', str(document.batch.id), page_filename)
            
            page_paths_data.append({
                'path': relative_page_path,
                'width': pix.width,
                'height': pix.height
            })
            logger.info(f"Page {page_number + 1} du document {document.id} sauvegardée.")

        pdf_document.close()

    except Exception as e:
        logger.error(f"PyMuPDF a échoué pour le document {document.id}. Erreur : {e}", exc_info=True)
        raise Exception(f"Impossible de convertir le PDF avec PyMuPDF. Le fichier est peut-être corrompu. Erreur : {e}")

    return page_paths_data

def _process_image_document(document: Document) -> list:
    """Traite un document qui est déjà une image."""
    image_path = document.file_path.path
    logger.info(f"Traitement du document image : {image_path}")

    try:
        with Image.open(image_path) as image:
            # Pour les images, la "page" est le document lui-même.
            return [{'path': document.file_path.name, 'width': image.width, 'height': image.height}]
    except Exception as e:
        logger.error(f"Impossible d'ouvrir le fichier image {image_path}: {e}", exc_info=True)
        raise

def create_audit_log(user, action, resource_type, resource_id, details=None):
    """
    Crée un log d'audit pour le suivi des activités
    """
    try:
        from .models import AuditLog
        
        AuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {}
        )
        logger.debug(f"Log d'audit créé: {action} sur {resource_type} {resource_id}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la création du log d'audit: {e}")
        return False