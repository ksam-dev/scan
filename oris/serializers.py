"""
Serializers pour l'API REST de ORIS
"""

from rest_framework import serializers
from .models import (
    Organization, Batch, Document, Page, OCRResult, 
    Annotation, AuditLog, HandwritingSample
)
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer pour les utilisateurs"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer pour les organisations"""
    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class OCRResultSerializer(serializers.ModelSerializer):
    """Serializer pour les résultats OCR"""
    class Meta:
        model = OCRResult
        fields = [
            'id', 'page', 'engine', 'raw_text', 'confidence_score',
            'processing_time', 'bounding_boxes', 'extracted_fields', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AnnotationSerializer(serializers.ModelSerializer):
    """Serializer pour les annotations"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Annotation
        fields = [
            'id', 'page', 'user', 'annotation_type', 'original_text',
            'corrected_text', 'field_name', 'field_value', 'bounding_box', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


class PageSerializer(serializers.ModelSerializer):
    """Serializer pour les pages"""
    ocr_results = OCRResultSerializer(many=True, read_only=True)
    annotations = AnnotationSerializer(many=True, read_only=True)
    
    class Meta:
        model = Page
        fields = [
            'id', 'document', 'page_number', 'image_path', 'status',
            'is_handwritten', 'created_at', 'updated_at', 'ocr_results', 'annotations'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PageListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des pages"""
    class Meta:
        model = Page
        fields = [
            'id', 'page_number', 'status', 'is_handwritten', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer pour les documents"""
    pages = PageListSerializer(many=True, read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'batch', 'original_filename', 'file_path', 'document_type',
            'status', 'total_pages', 'processed_pages', 'file_size',
            'created_at', 'updated_at', 'pages'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'file_size']


class DocumentListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des documents"""
    class Meta:
        model = Document
        fields = [
            'id', 'original_filename', 'document_type', 'status',
            'total_pages', 'processed_pages', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BatchSerializer(serializers.ModelSerializer):
    """Serializer pour les lots"""
    documents = DocumentListSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    
    class Meta:
        model = Batch
        fields = [
            'id', 'organization', 'user', 'name', 'status',
            'total_documents', 'processed_documents', 'created_at',
            'updated_at', 'documents'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class BatchListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des lots"""
    user = UserSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    
    class Meta:
        model = Batch
        fields = [
            'id', 'organization', 'user', 'name', 'status',
            'total_documents', 'processed_documents', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


class BatchCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de lots"""
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        help_text="Liste des fichiers à uploader"
    )
    
    class Meta:
        model = Batch
        fields = ['name', 'organization', 'files']
    
    def create(self, validated_data):
        files = validated_data.pop('files')
        user = self.context['request'].user
        
        # Création du batch
        batch = Batch.objects.create(
            user=user,
            **validated_data
        )
        
        # Traitement des fichiers sera fait dans la vue
        return batch


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer pour les logs d'audit"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'action', 'resource_type', 'resource_id',
            'details', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class HandwritingSampleSerializer(serializers.ModelSerializer):
    """Serializer pour les échantillons d'écriture manuscrite"""
    class Meta:
        model = HandwritingSample
        fields = [
            'id', 'page', 'image_crop', 'ground_truth_text', 'language',
            'writing_style', 'quality_score', 'used_for_training', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class OCRRequestSerializer(serializers.Serializer):
    """Serializer pour les requêtes OCR"""
    engine = serializers.ChoiceField(
        choices=['auto', 'tesseract', 'easyocr', 'trocr'],
        default='auto',
        help_text="Moteur OCR à utiliser ('auto' pour sélection automatique)"
    )
    force_reprocess = serializers.BooleanField(
        default=False,
        help_text="Forcer le retraitement même si des résultats existent"
    )


class ValidationRequestSerializer(serializers.Serializer):
    """Serializer pour les requêtes de validation"""
    corrected_text = serializers.CharField(
        help_text="Texte corrigé par l'utilisateur"
    )
    extracted_fields = serializers.JSONField(
        required=False,
        help_text="Champs structurés extraits"
    )
    annotations = serializers.ListField(
        child=serializers.JSONField(),
        required=False,
        help_text="Annotations supplémentaires"
    )

