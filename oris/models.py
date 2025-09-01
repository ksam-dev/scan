import uuid
import os
from django.db import models
from django.contrib.auth.models import AbstractUser, Permission, Group
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.utils import timezone


def document_upload_path(instance, filename):
    """Génère le chemin de stockage pour les documents"""
    return f'organizations/{instance.batch.organization.id}/batches/{instance.batch.id}/documents/{uuid.uuid4()}_{filename}'


def page_upload_path(instance, filename):
    """Génère le chemin de stockage pour les pages"""
    return f'organizations/{instance.document.batch.organization.id}/documents/{instance.document.id}/pages/{uuid.uuid4()}_{filename}'


def handwriting_sample_upload_path(instance, filename):
    """Génère le chemin de stockage pour les échantillons d'écriture"""
    return f'handwriting_samples/{uuid.uuid4()}_{filename}'


class Organization(models.Model):
    """Modèle pour les organisations/entreprises"""
    
    class Meta:
        verbose_name = _('Organisation')
        verbose_name_plural = _('Organisations')
        ordering = ['name']
    
    name = models.CharField(max_length=255, verbose_name=_('Nom'))
    slug = models.SlugField(unique=True, verbose_name=_('Slug'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    max_users = models.IntegerField(default=10, verbose_name=_('Nombre maximum d\'utilisateurs'))
    max_storage = models.BigIntegerField(default=10737418240, verbose_name=_('Espace de stockage maximum (octets)'))  # 10GB par défaut
    subscription_plan = models.CharField(
        max_length=20,
        choices=[
            ('free', _('Gratuit')),
            ('basic', _('Basique')),
            ('pro', _('Professionnel')),
            ('enterprise', _('Entreprise'))
        ],
        default='free',
        verbose_name=_('Plan d\'abonnement')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))
    
    def __str__(self):
        return self.name
    
    @property
    def used_storage(self):
        """Calcule l'espace de stockage utilisé par l'organisation"""
        from django.db.models import Sum
        total = self.batches.aggregate(
            total=Sum('documents__file_size')
        )['total'] or 0
        return total
    
    @property
    def storage_percentage(self):
        """Retourne le pourcentage d'espace de stockage utilisé"""
        if self.max_storage == 0:
            return 0
        return (self.used_storage / self.max_storage) * 100


from django.contrib.auth.models import BaseUserManager

class CustomUserManager(BaseUserManager):
    use_in_migrations = True
    
    def _create_user(self, username, email, password, **extra_fields):
        """Crée et sauvegarde un utilisateur avec le username, email et password"""
        if not email:
            raise ValueError(_('L\'email doit être renseigné'))
        if not username:
            raise ValueError(_('Le nom d\'utilisateur doit être renseigné'))
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'super_admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Le superutilisateur doit avoir is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Le superutilisateur doit avoir is_superuser=True.'))
        
        return self._create_user(username, email, password, **extra_fields)

class Utilisateur(AbstractUser):
    """Modèle utilisateur personnalisé avec rôles et organisation."""
    
    class Role(models.TextChoices):
        USER = 'user', _('Utilisateur')
        VALIDATOR = 'validator', _('Validateur')
        ADMIN = 'admin', _('Administrateur')
        SUPER_ADMIN = 'super_admin', _('Super Administrateur')
    
    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')
        ordering = ['username']
    
    # Champs personnalisés
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_('Organisation'),
        related_name='users'
    )
    role = models.CharField(
        max_length=20, 
        choices=Role.choices, 
        default=Role.USER, 
        verbose_name=_('Rôle')
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('Téléphone'))
    department = models.CharField(max_length=100, blank=True, verbose_name=_('Département'))
    job_title = models.CharField(max_length=100, blank=True, verbose_name=_('Poste'))
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        null=True, 
        blank=True, 
        verbose_name=_('Photo de profil')
    )
    email_verified = models.BooleanField(default=False, verbose_name=_('Email vérifié'))
    last_activity = models.DateTimeField(auto_now=True, verbose_name=_('Dernière activité'))
    two_factor_enabled = models.BooleanField(default=False, verbose_name=_('2FA activé'))
    
    # Relations
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('Groupes'),
        blank=True,
        help_text=_('Les groupes auxquels appartient l\'utilisateur.'),
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('Permissions utilisateur'),
        blank=True,
        help_text=_('Permissions spécifiques pour cet utilisateur.'),
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    
    objects = CustomUserManager()
    
    def __str__(self):
        return f"{self.username} ({self.organization.name if self.organization else 'Aucune organisation'})"
    
    @property
    def is_validator(self):
        """Vérifie si l'utilisateur est un validateur"""
        return self.role in [self.Role.VALIDATOR, self.Role.ADMIN, self.Role.SUPER_ADMIN]
    
    @property
    def is_org_admin(self):
        """Vérifie si l'utilisateur est un administrateur d'organisation"""
        return self.role in [self.Role.ADMIN, self.Role.SUPER_ADMIN]
    
    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur"""
        return f"{self.first_name} {self.last_name}".strip() or self.username


class Batch(models.Model):
    """Lot de documents uploadés ensemble"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('En attente')
        PROCESSING = 'processing', _('En cours de traitement')
        COMPLETED = 'completed', _('Terminé')
        FAILED = 'failed', _('Échec')
        PARTIAL = 'partial', _('Partiel')
    
    class Meta:
        verbose_name = _('Lot')
        verbose_name_plural = _('Lots')
        ordering = ['-created_at']
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='batches')
    user = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='batches')
    name = models.CharField(max_length=255, verbose_name=_('Nom'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_('Statut'))
    total_documents = models.IntegerField(default=0, verbose_name=_('Total des documents'))
    processed_documents = models.IntegerField(default=0, verbose_name=_('Documents traités'))
    priority = models.IntegerField(default=1, choices=[(1, _('Basse')), (2, _('Normale')), (3, _('Haute'))], verbose_name=_('Priorité'))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_('Métadonnées'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Date de completion'))
    
    def __str__(self):
        return f"{self.name} ({self.organization.name})"
    
    def save(self, *args, **kwargs):
        """Met à jour la date de completion si le statut est terminé"""
        if self.status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def progress_percentage(self):
        """Calcule le pourcentage de progression du traitement"""
        if self.total_documents == 0:
            return 0
        return (self.processed_documents / self.total_documents) * 100
    @property
    def validated_documents_count(self):
        return self.documents.filter(status=Document.Status.VALIDATED).count()
    
    @property
    def pending_validation_count(self):
        return self.documents.filter(status=Document.Status.VALIDATION_PENDING).count()


class Document(models.Model):
    """Document individuel dans un lot"""
    
    class DocumentType(models.TextChoices):
        PDF = 'pdf', 'PDF'
        IMAGE = 'image', _('Image')
        SCAN = 'scan', _('Scan')
        TEXT = 'text', _('Texte')
    
    class Status(models.TextChoices):
        UPLOADED = 'uploaded', _('Uploadé')
        PROCESSING = 'processing', _('En cours de traitement')
        OCR_COMPLETED = 'ocr_completed', _('OCR terminé')
        VALIDATION_PENDING = 'validation_pending', _('Validation en attente')
        VALIDATED = 'validated', _('Validé')
        FAILED = 'failed', _('Échec')
    
    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ['-created_at']
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='documents')
    original_filename = models.CharField(max_length=255, verbose_name=_('Nom de fichier original'))
    file_path = models.FileField(
        upload_to=document_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif', 'bmp'])],
        verbose_name=_('Fichier')
    )
    document_type = models.CharField(max_length=10, choices=DocumentType.choices, verbose_name=_('Type de document'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED, verbose_name=_('Statut'))
    total_pages = models.IntegerField(default=0, verbose_name=_('Total des pages'))
    processed_pages = models.IntegerField(default=0, verbose_name=_('Pages traitées'))
    file_size = models.BigIntegerField(verbose_name=_('Taille du fichier'))
    mime_type = models.CharField(max_length=100, blank=True, verbose_name=_('Type MIME'))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_('Métadonnées'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))
    
    def __str__(self):
        return f"{self.original_filename} ({self.batch.name})"
    
    def delete(self, *args, **kwargs):
        """Supprime le fichier physique lors de la suppression de l'objet"""
        if self.file_path:
            if os.path.isfile(self.file_path.path):
                os.remove(self.file_path.path)
        super().delete(*args, **kwargs)
    
    @property
    def file_size_human(self):
        """Retourne la taille du fichier formatée"""
        sizes = ['B', 'KB', 'MB', 'GB']
        size = self.file_size
        i = 0
        while size >= 1024 and i < len(sizes)-1:
            size /= 1024
            i += 1
        return f"{size:.2f} {sizes[i]}"


class Page(models.Model):
    """Page individuelle d'un document"""
    
    class Status(models.TextChoices):
        EXTRACTED = 'extracted', _('Extraite')
        OCR_PENDING = 'ocr_pending', _('OCR en attente')
        OCR_PROCESSING = 'ocr_processing', _('OCR en cours')
        OCR_COMPLETED = 'ocr_completed', _('OCR terminé')
        VALIDATION_PENDING = 'validation_pending', _('Validation en attente')
        VALIDATED = 'validated', _('Validée')
        FAILED = 'failed', _('Échec')
    
    class Meta:
        verbose_name = _('Page')
        verbose_name_plural = _('Pages')
        ordering = ['document', 'page_number']
        unique_together = ['document', 'page_number']
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='pages')
    page_number = models.IntegerField(verbose_name=_('Numéro de page'))
    image_path = models.FileField(upload_to=page_upload_path, verbose_name=_('Chemin de l\'image'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EXTRACTED, verbose_name=_('Statut'))
    is_handwritten = models.BooleanField(null=True, blank=True, verbose_name=_('Écriture manuscrite'))
    width = models.IntegerField(default=0, verbose_name=_('Largeur'))
    height = models.IntegerField(default=0, verbose_name=_('Hauteur'))
    dpi = models.IntegerField(null=True, blank=True, verbose_name=_('DPI'))
    quality_score = models.FloatField(null=True, blank=True, verbose_name=_('Score de qualité'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))
    
    def __str__(self):
        return f"Page {self.page_number} - {self.document.original_filename}"


class OCRResult(models.Model):
    """Résultats OCR/HTR pour une page"""
    
    class Engine(models.TextChoices):
        TESSERACT = 'tesseract', 'Tesseract'
        EASYOCR = 'easyocr', 'EasyOCR'
        PADDLEOCR = 'paddleocr', 'PaddleOCR'
        TROCR = 'trocr', 'TrOCR'
        KRAKEN = 'kraken', 'Kraken'
        DONUT = 'donut', 'Donut'
        CUSTOM = 'custom', _('Personnalisé')
    
    class Meta:
        verbose_name = _('Résultat OCR')
        verbose_name_plural = _('Résultats OCR')
        unique_together = ['page', 'engine']
        ordering = ['-created_at']
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='ocr_results')
    engine = models.CharField(max_length=20, choices=Engine.choices, verbose_name=_('Moteur OCR'))
    engine_version = models.CharField(max_length=50, blank=True, verbose_name=_('Version du moteur'))
    raw_text = models.TextField(verbose_name=_('Texte brut'))
    confidence_score = models.FloatField(null=True, blank=True, verbose_name=_('Score de confiance'))
    processing_time = models.FloatField(verbose_name=_('Temps de traitement (secondes)'))
    language = models.CharField(max_length=10, default='fra', verbose_name=_('Langue'))
    bounding_boxes = models.JSONField(default=dict, verbose_name=_('Boîtes de délimitation'))
    extracted_fields = models.JSONField(default=dict, verbose_name=_('Champs extraits'))
    post_processed_text = models.TextField(blank=True, verbose_name=_('Texte post-traité'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    
    def __str__(self):
        return f"{self.engine} - {self.page}"


class Annotation(models.Model):
    """Corrections et annotations humaines"""
    
    class Type(models.TextChoices):
        CORRECTION = 'correction', _('Correction')
        FIELD_EXTRACTION = 'field_extraction', _('Extraction de champ')
        VALIDATION = 'validation', _('Validation')
        COMMENT = 'comment', _('Commentaire')
        HIGHLIGHT = 'highlight', _('Surlignage')
    
    class Meta:
        verbose_name = _('Annotation')
        verbose_name_plural = _('Annotations')
        ordering = ['-created_at']
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='annotations')
    user = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='annotations')
    annotation_type = models.CharField(max_length=20, choices=Type.choices, verbose_name=_('Type d\'annotation'))
    original_text = models.TextField(blank=True, verbose_name=_('Texte original'))
    corrected_text = models.TextField(blank=True, verbose_name=_('Texte corrigé'))
    field_name = models.CharField(max_length=100, blank=True, verbose_name=_('Nom du champ'))
    field_value = models.TextField(blank=True, verbose_name=_('Valeur du champ'))
    bounding_box = models.JSONField(default=dict, verbose_name=_('Boîte de délimitation'))
    confidence = models.FloatField(null=True, blank=True, verbose_name=_('Confiance'))
    is_accepted = models.BooleanField(default=False, verbose_name=_('Accepté'))
    comment = models.TextField(blank=True, verbose_name=_('Commentaire'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))
    
    def __str__(self):
        return f"{self.annotation_type} - {self.page} par {self.user.username}"


class AuditLog(models.Model):
    """Journal d'audit pour traçabilité"""
    
    class Action(models.TextChoices):
        UPLOAD = 'upload', _('Upload')
        OCR_START = 'ocr_start', _('Début OCR')
        OCR_COMPLETE = 'ocr_complete', _('OCR terminé')
        VALIDATION_START = 'validation_start', _('Début validation')
        VALIDATION_COMPLETE = 'validation_complete', _('Validation terminée')
        EXPORT = 'export', _('Export')
        ERROR = 'error', _('Erreur')
        LOGIN = 'login', _('Connexion')
        LOGOUT = 'logout', _('Déconnexion')
        CREATE = 'create', _('Création')
        UPDATE = 'update', _('Modification')
        DELETE = 'delete', _('Suppression')
    
    class Meta:
        verbose_name = _('Journal d\'audit')
        verbose_name_plural = _('Journaux d\'audit')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'action']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=Action.choices, verbose_name=_('Action'))
    resource_type = models.CharField(max_length=50, verbose_name=_('Type de ressource'))
    resource_id = models.UUIDField(verbose_name=_('ID de la ressource'))
    details = models.JSONField(default=dict, verbose_name=_('Détails'))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('Adresse IP'))
    user_agent = models.TextField(blank=True, verbose_name=_('User Agent'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Horodatage'))
    
    def __str__(self):
        return f"{self.action} - {self.resource_type} {self.resource_id}"


class HandwritingSample(models.Model):
    """Échantillons d'écriture manuscrite pour l'entraînement"""
    
    class Meta:
        verbose_name = _('Échantillon d\'écriture')
        verbose_name_plural = _('Échantillons d\'écriture')
        ordering = ['-created_at']
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='handwriting_samples')
    image_crop = models.FileField(upload_to=handwriting_sample_upload_path, verbose_name=_('Extrait d\'image'))
    ground_truth_text = models.TextField(verbose_name=_('Texte de vérité terrain'))
    language = models.CharField(max_length=10, default='fra', verbose_name=_('Langue'))
    writing_style = models.CharField(max_length=50, blank=True, verbose_name=_('Style d\'écriture'))
    quality_score = models.FloatField(null=True, blank=True, verbose_name=_('Score de qualité'))
    used_for_training = models.BooleanField(default=False, verbose_name=_('Utilisé pour l\'entraînement'))
    training_model_version = models.CharField(max_length=50, blank=True, verbose_name=_('Version du modèle d\'entraînement'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    
    def __str__(self):
        return f"Sample {self.id} - {self.page}"


class APIKey(models.Model):
    """Clés API pour l'accès externe"""
    
    class Meta:
        verbose_name = _('Clé API')
        verbose_name_plural = _('Clés API')
        ordering = ['-created_at']
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100, verbose_name=_('Nom'))
    key = models.CharField(max_length=64, unique=True, verbose_name=_('Clé'))
    secret = models.CharField(max_length=64, verbose_name=_('Secret'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    permissions = models.JSONField(default=dict, verbose_name=_('Permissions'))
    rate_limit = models.IntegerField(default=1000, verbose_name=_('Limite de requêtes'))
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Date d\'expiration'))
    last_used = models.DateTimeField(null=True, blank=True, verbose_name=_('Dernière utilisation'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    
    def __str__(self):
        return f"{self.name} - {self.organization.name}"
    
    def is_expired(self):
        """Vérifie si la clé API est expirée"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class ExportProfile(models.Model):
    """Profils d'export pour la configuration des sorties"""
    
    class Format(models.TextChoices):
        JSON = 'json', 'JSON'
        XML = 'xml', 'XML'
        CSV = 'csv', 'CSV'
        PDF = 'pdf', 'PDF'
        TEXT = 'text', _('Texte')
    
    class Meta:
        verbose_name = _('Profil d\'export')
        verbose_name_plural = _('Profils d\'export')
        ordering = ['name']
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='export_profiles')
    name = models.CharField(max_length=100, verbose_name=_('Nom'))
    format = models.CharField(max_length=10, choices=Format.choices, verbose_name=_('Format'))
    field_mapping = models.JSONField(default=dict, verbose_name=_('Mapping des champs'))
    include_metadata = models.BooleanField(default=True, verbose_name=_('Inclure les métadonnées'))
    include_annotations = models.BooleanField(default=False, verbose_name=_('Inclure les annotations'))
    compression_enabled = models.BooleanField(default=False, verbose_name=_('Compression activée'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))
    
    def __str__(self):
        return f"{self.name} ({self.get_format_display()}) - {self.organization.name}"