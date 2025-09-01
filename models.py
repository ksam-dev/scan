from django.db import models
from django.contrib.auth.models import User
import uuid


class Organization(models.Model):
    """Modèle pour les organisations/entreprises"""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


class Batch(models.Model):
    """Lot de documents uploadés ensemble"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours de traitement'),
        ('completed', 'Terminé'),
        ('failed', 'Échec'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_documents = models.IntegerField(default=0)
    processed_documents = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class Document(models.Model):
    """Document individuel dans un lot"""
    TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('image', 'Image'),
        ('scan', 'Scan'),
    ]
    
    STATUS_CHOICES = [
        ('uploaded', 'Uploadé'),
        ('processing', 'En cours de traitement'),
        ('ocr_completed', 'OCR terminé'),
        ('validated', 'Validé'),
        ('failed', 'Échec'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='documents')
    original_filename = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='documents/')
    document_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    total_pages = models.IntegerField(default=0)
    processed_pages = models.IntegerField(default=0)
    file_size = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.original_filename} ({self.batch.name})"


class Page(models.Model):
    """Page individuelle d'un document"""
    STATUS_CHOICES = [
        ('extracted', 'Extraite'),
        ('ocr_pending', 'OCR en attente'),
        ('ocr_processing', 'OCR en cours'),
        ('ocr_completed', 'OCR terminé'),
        ('validation_pending', 'Validation en attente'),
        ('validated', 'Validée'),
        ('failed', 'Échec'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='pages')
    page_number = models.IntegerField()
    image_path = models.FileField(upload_to='pages/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='extracted')
    is_handwritten = models.BooleanField(null=True, blank=True)  # None = non déterminé
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['document', 'page_number']
        ordering = ['document', 'page_number']
    
    def __str__(self):
        return f"Page {self.page_number} - {self.document.original_filename}"


class OCRResult(models.Model):
    """Résultats OCR/HTR pour une page"""
    ENGINE_CHOICES = [
        ('tesseract', 'Tesseract'),
        ('easyocr', 'EasyOCR'),
        ('paddleocr', 'PaddleOCR'),
        ('trocr', 'TrOCR'),
        ('kraken', 'Kraken'),
        ('donut', 'Donut'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='ocr_results')
    engine = models.CharField(max_length=20, choices=ENGINE_CHOICES)
    raw_text = models.TextField()
    confidence_score = models.FloatField(null=True, blank=True)
    processing_time = models.FloatField()  # en secondes
    bounding_boxes = models.JSONField(default=dict)  # Coordonnées des zones de texte
    extracted_fields = models.JSONField(default=dict)  # Champs structurés extraits
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['page', 'engine']
    
    def __str__(self):
        return f"{self.engine} - {self.page}"


class Annotation(models.Model):
    """Corrections et annotations humaines"""
    TYPE_CHOICES = [
        ('correction', 'Correction'),
        ('field_extraction', 'Extraction de champ'),
        ('validation', 'Validation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='annotations')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    annotation_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    original_text = models.TextField()
    corrected_text = models.TextField()
    field_name = models.CharField(max_length=100, blank=True)
    field_value = models.TextField(blank=True)
    bounding_box = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.annotation_type} - {self.page} par {self.user.username}"


class AuditLog(models.Model):
    """Journal d'audit pour traçabilité"""
    ACTION_CHOICES = [
        ('upload', 'Upload'),
        ('ocr_start', 'Début OCR'),
        ('ocr_complete', 'OCR terminé'),
        ('validation_start', 'Début validation'),
        ('validation_complete', 'Validation terminée'),
        ('export', 'Export'),
        ('error', 'Erreur'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50)  # 'batch', 'document', 'page'
    resource_id = models.UUIDField()
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.action} - {self.resource_type} {self.resource_id}"


class HandwritingSample(models.Model):
    """Échantillons d'écriture manuscrite pour l'entraînement"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    image_crop = models.FileField(upload_to='handwriting_samples/')
    ground_truth_text = models.TextField()
    language = models.CharField(max_length=10, default='fr')
    writing_style = models.CharField(max_length=50, blank=True)
    quality_score = models.FloatField(null=True, blank=True)
    used_for_training = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Sample {self.id} - {self.page}"
