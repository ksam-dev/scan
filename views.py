"""
Vues API pour ORIS
"""

import os
import uuid
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .models import (
    Organization, Batch, Document, Page, OCRResult, 
    Annotation, AuditLog, HandwritingSample
)
from .serializers import (
    OrganizationSerializer, BatchSerializer, BatchListSerializer, BatchCreateSerializer,
    DocumentSerializer, DocumentListSerializer, PageSerializer, PageListSerializer,
    OCRResultSerializer, AnnotationSerializer, AuditLogSerializer,
    HandwritingSampleSerializer, OCRRequestSerializer, ValidationRequestSerializer
)
from .utils import process_uploaded_file, create_audit_log
import logging

logger = logging.getLogger(__name__)


class OrganizationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les organisations"""
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]


class BatchViewSet(viewsets.ModelViewSet):
    """ViewSet pour les lots de documents"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Filtrer les lots par utilisateur/organisation"""
        user = self.request.user
        return Batch.objects.filter(user=user).order_by('-created_at')
    
    def get_serializer_class(self):
        """Choisir le serializer selon l'action"""
        if self.action == 'create':
            return BatchCreateSerializer
        elif self.action == 'list':
            return BatchListSerializer
        return BatchSerializer
    
    def create(self, request, *args, **kwargs):
        """Créer un nouveau lot avec upload de fichiers"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Création du batch
        batch = serializer.save()
        
        # Traitement des fichiers uploadés
        files = request.FILES.getlist('files')
        if not files:
            return Response(
                {'error': 'Aucun fichier fourni'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_documents = []
        for file in files:
            try:
                document = process_uploaded_file(file, batch)
                created_documents.append(document)
            except Exception as e:
                logger.error(f"Erreur lors du traitement du fichier {file.name}: {e}")
                # Continuer avec les autres fichiers
        
        # Mise à jour du batch
        batch.total_documents = len(created_documents)
        batch.save()
        
        # Log d'audit
        create_audit_log(
            user=request.user,
            action='upload',
            resource_type='batch',
            resource_id=batch.id,
            details={
                'files_count': len(files),
                'documents_created': len(created_documents)
            }
        )
        
        # Retourner le batch créé
        response_serializer = BatchSerializer(batch)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Lancer le traitement OCR d'un lot"""
        batch = self.get_object()
        
        if batch.status != 'pending':
            return Response(
                {'error': 'Le lot n\'est pas en attente de traitement'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Lancer le traitement asynchrone (sera implémenté en phase 4)
        # from ocr.tasks import process_batch
        # process_batch.delay(batch.id)
        
        batch.status = 'processing'
        batch.save()
        
        create_audit_log(
            user=request.user,
            action='ocr_start',
            resource_type='batch',
            resource_id=batch.id
        )
        
        return Response({'message': 'Traitement lancé'})


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les documents (lecture seule)"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrer les documents par utilisateur"""
        user = self.request.user
        return Document.objects.filter(batch__user=user).order_by('-created_at')
    
    def get_serializer_class(self):
        """Choisir le serializer selon l'action"""
        if self.action == 'list':
            return DocumentListSerializer
        return DocumentSerializer
    
    @action(detail=True, methods=['get'])
    def pages(self, request, pk=None):
        """Récupérer les pages d'un document"""
        document = self.get_object()
        pages = document.pages.all().order_by('page_number')
        serializer = PageListSerializer(pages, many=True)
        return Response(serializer.data)


class PageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les pages"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrer les pages par utilisateur"""
        user = self.request.user
        return Page.objects.filter(document__batch__user=user).order_by('document', 'page_number')
    
    def get_serializer_class(self):
        """Choisir le serializer selon l'action"""
        if self.action == 'list':
            return PageListSerializer
        return PageSerializer
    
    @action(detail=True, methods=['post'])
    def ocr(self, request, pk=None):
        """Lancer l'OCR sur une page spécifique"""
        page = self.get_object()
        serializer = OCRRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        engine = serializer.validated_data['engine']
        force_reprocess = serializer.validated_data['force_reprocess']
        
        # Vérifier si des résultats existent déjà
        if not force_reprocess and page.ocr_results.exists():
            return Response(
                {'message': 'Des résultats OCR existent déjà. Utilisez force_reprocess=true pour retraiter.'},
                status=status.HTTP_200_OK
            )
        
        # Lancer le traitement OCR (sera implémenté en phase 4)
        # from ocr.tasks import process_page_ocr
        # process_page_ocr.delay(page.id, engine)
        
        page.status = 'ocr_processing'
        page.save()
        
        create_audit_log(
            user=request.user,
            action='ocr_start',
            resource_type='page',
            resource_id=page.id,
            details={'engine': engine}
        )
        
        return Response({'message': 'Traitement OCR lancé'})
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Récupérer les résultats OCR d'une page"""
        page = self.get_object()
        results = page.ocr_results.all().order_by('-created_at')
        serializer = OCRResultSerializer(results, many=True)
        return Response(serializer.data)


class ValidationViewSet(viewsets.ViewSet):
    """ViewSet pour la validation humaine"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Récupérer les pages en attente de validation"""
        user = request.user
        pages = Page.objects.filter(
            document__batch__user=user,
            status='validation_pending'
        ).order_by('created_at')
        
        serializer = PageListSerializer(pages, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """Valider une page"""
        serializer = ValidationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        page_id = request.data.get('page_id')
        if not page_id:
            return Response(
                {'error': 'page_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        page = get_object_or_404(
            Page,
            id=page_id,
            document__batch__user=request.user
        )
        
        # Créer l'annotation de validation
        annotation = Annotation.objects.create(
            page=page,
            user=request.user,
            annotation_type='validation',
            original_text=page.ocr_results.first().raw_text if page.ocr_results.exists() else '',
            corrected_text=serializer.validated_data['corrected_text'],
            field_name='',
            field_value='',
            bounding_box={}
        )
        
        # Mettre à jour le statut de la page
        page.status = 'validated'
        page.save()
        
        # Mettre à jour les champs extraits si fournis
        extracted_fields = serializer.validated_data.get('extracted_fields', {})
        if extracted_fields and page.ocr_results.exists():
            ocr_result = page.ocr_results.first()
            ocr_result.extracted_fields.update(extracted_fields)
            ocr_result.save()
        
        create_audit_log(
            user=request.user,
            action='validation_complete',
            resource_type='page',
            resource_id=page.id,
            details={'annotation_id': str(annotation.id)}
        )
        
        return Response({'message': 'Page validée avec succès'})


class OCRResultViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les résultats OCR"""
    serializer_class = OCRResultSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrer les résultats par utilisateur"""
        user = self.request.user
        return OCRResult.objects.filter(
            page__document__batch__user=user
        ).order_by('-created_at')


class AnnotationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les annotations"""
    serializer_class = AnnotationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrer les annotations par utilisateur"""
        user = self.request.user
        return Annotation.objects.filter(
            page__document__batch__user=user
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Associer l'utilisateur à l'annotation"""
        serializer.save(user=self.request.user)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les logs d'audit"""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrer les logs par utilisateur"""
        user = self.request.user
        return AuditLog.objects.filter(user=user).order_by('-timestamp')


class HandwritingSampleViewSet(viewsets.ModelViewSet):
    """ViewSet pour les échantillons d'écriture manuscrite"""
    serializer_class = HandwritingSampleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrer les échantillons par utilisateur"""
        user = self.request.user
        return HandwritingSample.objects.filter(
            page__document__batch__user=user
        ).order_by('-created_at')


# Vues pour les webhooks et callbacks
def webhook_batch_complete(request, batch_id):
    """Webhook appelé quand un lot est terminé"""
    try:
        batch = Batch.objects.get(id=batch_id)
        
        # Logique de notification (email, webhook externe, etc.)
        # À implémenter selon les besoins
        
        return JsonResponse({
            'status': 'success',
            'batch_id': str(batch_id),
            'message': 'Webhook traité'
        })
    except Batch.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Lot non trouvé'
        }, status=404)



def webhook_document_complete(request, document_id):
    """Webhook appelé quand un document est terminé"""
    try:
        document = Document.objects.get(id=document_id)
        
        # Logique de notification
        # À implémenter selon les besoins
        
        return JsonResponse({
            'status': 'success',
            'document_id': str(document_id),
            'message': 'Webhook traité'
        })
    except Document.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Document non trouvé'
        }, status=404)

