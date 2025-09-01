# ORIS - Système OCR - Vues Django

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.generic import TemplateView, View, ListView, DetailView
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
import json
import logging
import os
import uuid
from django.utils.text import slugify
from django.db.models import Q, Count, Avg, Sum, F, ExpressionWrapper, FloatField

# Importer vos modèles
from .models import (
    Utilisateur, Organization, Batch, Document, Page, 
    OCRResult, Annotation, AuditLog, HandwritingSample, ExportProfile, APIKey
)
from .utils import process_uploaded_file
from .tasks import process_batch_task
from .serializers import (
    OrganizationSerializer, BatchSerializer, BatchListSerializer, BatchCreateSerializer,
    DocumentSerializer, DocumentListSerializer, PageSerializer, PageListSerializer,
    OCRResultSerializer, AnnotationSerializer, AuditLogSerializer,
    HandwritingSampleSerializer, OCRRequestSerializer, ValidationRequestSerializer
)

logger = logging.getLogger(__name__)

# ============================================================================
# VUES D'AUTHENTIFICATION
# ============================================================================

class LoginView(TemplateView):
    template_name = 'auth/login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        email = request.POST.get('username') 
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, 'Veuillez remplir tous les champs.')
            return self.get(request, *args, **kwargs)

        # Authentifier avec l'email comme nom d'utilisateur
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            # Enregistrer l'action de connexion dans l'historique
            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.LOGIN,
                resource_type='user',
                resource_id=user.id,
                details={'ip_address': request.META.get('REMOTE_ADDR')}
            )
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')
            return self.get(request, *args, **kwargs)

class RegisterView(TemplateView):
    template_name = 'auth/register.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logger.info("Début du processus d'inscription")
        
        # Récupération des données
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        organization_name = request.POST.get('organization', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        logger.info(f"Données reçues: first_name={first_name}, last_name={last_name}, email={email}")

        # Validation des champs obligatoires
        required_fields = [first_name, last_name, email, password, password_confirm]
        if not all(required_fields):
            logger.warning("Champs obligatoires manquants")
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return render(request, self.template_name, {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'organization': organization_name,
            })

        if password != password_confirm:
            logger.warning("Mots de passe ne correspondent pas")
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return render(request, self.template_name, {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'organization': organization_name,
            })
        
        if len(password) < 8:
            logger.warning("Mot de passe trop court")
            messages.error(request, "Le mot de passe doit contenir au moins 8 caractères.")
            return render(request, self.template_name, {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'organization': organization_name,
            })

        # Vérification si l'email existe déjà
        if Utilisateur.objects.filter(email=email).exists():
            logger.warning(f"Email déjà existant: {email}")
            messages.error(request, "Un utilisateur avec cet email existe déjà.")
            return render(request, self.template_name, {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'organization': organization_name,
            })

        try:
            logger.info("Tentative de création de l'organisation")
            
            # Créer ou récupérer l'organisation
            if not organization_name:
                organization_name = f"Organisation de {first_name} {last_name}"
            
            organization, org_created = Organization.objects.get_or_create(
                name=organization_name,
                defaults={
                    'slug': slugify(organization_name),
                    'is_active': True
                }
            )
            
            logger.info(f"Organisation {'créée' if org_created else 'trouvée'}: {organization.name}")

            logger.info("Tentative de création de l'utilisateur")
            
            # Créer l'utilisateur avec create_user (qui hash le mot de passe)
            user = Utilisateur.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                organization=organization,
                role=Utilisateur.Role.ADMIN,
                is_staff=True,
                is_active=True
            )
            
            logger.info(f"Utilisateur créé avec succès: {user.email}")

            # Connecter l'utilisateur
            login(request, user)
            
            logger.info("Utilisateur connecté avec succès")

            # Journaliser l'action
            AuditLog.objects.create(
                user=user, 
                action=AuditLog.Action.CREATE, 
                resource_type='user',
                resource_id=user.id, 
                details={'source': 'register'}
            )

            messages.success(request, f"Bienvenue, {user.first_name} ! Votre compte a été créé.")
            return redirect('dashboard')

        except Exception as e:
            logger.error(f"Erreur lors de l'inscription : {str(e)}", exc_info=True)
            messages.error(request, f"Une erreur est survenue lors de la création du compte: {str(e)}")
            return render(request, self.template_name, {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'organization': organization_name,
            })

def logout_view(request):
    if request.user.is_authenticated:
        AuditLog.objects.create(
            user=request.user, 
            action=AuditLog.Action.LOGOUT, 
            resource_type='user',
            resource_id=request.user.id, 
            details={'ip_address': request.META.get('REMOTE_ADDR')}
        )
        logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('login')

# ============================================================================
# DASHBOARD
# ============================================================================

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Récupérer les lots de l'utilisateur
        user_batches = Batch.objects.filter(user=user)
        
        # Calculer les statistiques réelles
        total_batches = user_batches.count()
        total_documents = Document.objects.filter(batch__in=user_batches).count()
        pending_validation = Document.objects.filter(
            batch__in=user_batches, 
            status=Document.Status.VALIDATION_PENDING
        ).count()
        
        # Calcul de la précision moyenne
        avg_confidence = OCRResult.objects.filter(
            page__document__batch__in=user_batches
        ).aggregate(avg_conf=Avg('confidence_score'))['avg_conf'] or 0
        
        # Calcul de l'espace de stockage utilisé
        storage_used = Document.objects.filter(
            batch__in=user_batches
        ).aggregate(total_size=Sum('file_size'))['total_size'] or 0
        
        context['stats'] = {
            'total_batches': total_batches,
            'total_documents': total_documents,
            'pending_validation': pending_validation,
            'accuracy_rate': round(avg_confidence * 100, 2) if avg_confidence else 0,
            'storage_used': storage_used,
            'storage_percentage': round((storage_used / user.organization.max_storage) * 100, 2) if user.organization else 0,
        }
        
        # Activité récente
        context['recent_activities'] = AuditLog.objects.filter(user=user).order_by('-timestamp')[:5]
        
        # Lots récents
        context['recent_batches'] = user_batches.order_by('-created_at')[:5]
        
        return context

# ============================================================================
# GESTION DES LOTS
# ============================================================================

class BatchUploadView(LoginRequiredMixin, TemplateView):
    template_name = 'batch/upload.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organizations'] = Organization.objects.filter(users=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist('documents')
        batch_name = request.POST.get('batch_name')
        organization_id = request.POST.get('organization')
        description = request.POST.get('description', '')

        if not files:
            messages.error(request, "Veuillez sélectionner au moins un fichier.")
            return redirect('batch_upload')
        
        if not batch_name:
            messages.error(request, "Veuillez donner un nom au lot.")
            return redirect('batch_upload')

        try:
            organization = Organization.objects.get(id=organization_id, users=request.user)
        except (Organization.DoesNotExist, ValueError):
            messages.error(request, "Organisation non valide.")
            return redirect('batch_upload')

        # Créer le lot
        batch = Batch.objects.create(
            name=batch_name,
            description=description,
            user=request.user,
            organization=organization,
            status=Batch.Status.PENDING,
            total_documents=len(files)
        )

        docs_created_count = 0
        for f in files:
            try:
                document = process_uploaded_file(f, batch)
                if document:
                    docs_created_count += 1
            except Exception as e:
                logger.error(f"Échec de préparation du fichier {f.name}: {e}")
                messages.warning(request, f"Le fichier {f.name} n'a pas pu être préparé: {str(e)}")
        
        if docs_created_count == 0:
            batch.status = Batch.Status.FAILED
            batch.save()
            messages.error(request, "Aucun document n'a pu être traité. Le lot a échoué.")
            return redirect('batch_upload')

        # Mettre à jour le compteur de documents
        batch.total_documents = docs_created_count
        batch.save()

        # Lancer la tâche de fond
        try:
            process_batch_task.delay(batch.id)
            messages.success(request, f"Le lot '{batch.name}' a été créé. Le traitement a commencé.")
        except Exception as e:
            logger.error(f"Erreur lors du lancement de la tâche: {e}")
            messages.warning(request, "Le lot a été créé mais le traitement n'a pas pu démarrer automatiquement.")

        return redirect('batch_list')

class BatchListView(LoginRequiredMixin, View):
    template_name = 'batch/list.html'
    paginate_by = 10

    def get(self, request, *args, **kwargs):
        user = request.user
        
        # 1. Obtenir le queryset de base
        base_queryset = Batch.objects.filter(user=user).order_by('-created_at')

        # 2. Appliquer les filtres de recherche (si nécessaire)
        search_query = request.GET.get('search')
        if search_query:
            base_queryset = base_queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        status_filter = request.GET.get('status')
        if status_filter:
            base_queryset = base_queryset.filter(status=status_filter)

        # 3. Préparer les données pour chaque lot
        batches_with_stats = []
        for batch in base_queryset:
            # Calculer les statistiques pour chaque lot individuellement
            validated_count = batch.documents.filter(status=Document.Status.VALIDATED).count()
            pending_count = batch.documents.filter(status=Document.Status.VALIDATION_PENDING).count()
            
            # Calcul de la précision moyenne
            avg_accuracy_result = OCRResult.objects.filter(page__document__batch=batch).aggregate(
                avg_conf=Avg('confidence_score')
            )
            avg_accuracy = (avg_accuracy_result['avg_conf'] or 0) * 100

            batches_with_stats.append({
                'object': batch, # L'objet batch original
                'validated_documents_count': validated_count,
                'pending_validation_count': pending_count,
                'average_accuracy': avg_accuracy,
                # On utilise la propriété du modèle, c'est plus simple ici
                'progress_percentage': batch.progress_percentage 
            })

        # 4. Mettre en place la pagination
        paginator = Paginator(batches_with_stats, self.paginate_by)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'batches_with_stats': page_obj, # Passer la page paginée au template
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages()
        }
        
        return render(request, self.template_name, context)

class BatchDetailView(LoginRequiredMixin, DetailView):
    model = Batch
    template_name = 'batch/detail.html'
    context_object_name = 'batch'
    pk_url_kwarg = 'batch_id' # Assurez-vous que cela correspond à votre URL

    def get_queryset(self):
        # S'assurer que l'utilisateur ne peut voir que ses propres lots
        return Batch.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        batch = self.get_object()
        
        # Documents du lot
        context['documents'] = batch.documents.all().order_by('original_filename')
        
        # Statistiques agrégées pour le lot
        stats = Page.objects.filter(document__batch=batch).aggregate(
            total_pages=Count('id'),
            pending_validation=Count('id', filter=Q(status=Page.Status.VALIDATION_PENDING)),
            avg_confidence=Avg('ocr_results__confidence_score')
        )
        
        context['stats'] = {
            'total_pages': stats.get('total_pages', 0),
            'pending_validation': stats.get('pending_validation', 0),
            'avg_confidence': (stats.get('avg_confidence') or 0) * 100
        }
        
        return context
class BatchReprocessView(LoginRequiredMixin, View):
    def post(self, request, batch_id):
        batch = get_object_or_404(Batch, id=batch_id, user=request.user)
        
        # Réinitialiser le statut des documents et pages
        batch.documents.update(status=Document.Status.UPLOADED)
        Page.objects.filter(document__batch=batch).update(status=Page.Status.OCR_PENDING)
        
        # Relancer le traitement
        batch.status = Batch.Status.PENDING
        batch.processed_documents = 0
        batch.save()
        
        try:
            process_batch_task.delay(batch.id)
            messages.success(request, f"Retraitement du lot '{batch.name}' lancé.")
        except Exception as e:
            logger.error(f"Erreur lors du relancement du traitement: {e}")
            messages.error(request, "Erreur lors du lancement du retraitement.")
        
        return redirect('batch_detail', batch_id=batch_id)

class BatchDeleteView(LoginRequiredMixin, View):
    def delete(self, request, batch_id):
        batch = get_object_or_404(Batch, id=batch_id, user=request.user)
        batch_name = batch.name
        batch.delete()
        
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.DELETE,
            resource_type='batch',
            resource_id=batch_id,
            details={'batch_name': batch_name}
        )
        
        return JsonResponse({'success': True, 'message': 'Lot supprimé'})
import csv  # <--- AJOUTER CET IMPORT
class BatchExportView(LoginRequiredMixin, View ):
    def get(self, request, batch_id):
        batch = get_object_or_404(Batch, id=batch_id, user=request.user)
        
        # Créer la réponse HTTP avec le bon header pour un fichier CSV
        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="export_lot_{batch.id}.csv"'},
        )

        writer = csv.writer(response)
        
        # Écrire l'en-tête du CSV
        writer.writerow([
            'ID Document', 'Nom Fichier', 'Statut', 'Nombre Pages', 
            'Texte OCR', 'Score Confiance Moyen'
        ])

        # Récupérer tous les documents et leurs résultats OCR pour ce lot
        documents = batch.documents.all().annotate(
            avg_confidence=Avg('pages__ocr_results__confidence_score')
        )

        for doc in documents:
            # Récupérer le texte de la première page pour l'exemple
            first_page = doc.pages.first()
            ocr_text = ""
            if first_page and first_page.ocr_results.exists():
                ocr_text = first_page.ocr_results.first().raw_text

            writer.writerow([
                doc.id,
                doc.original_filename,
                doc.get_status_display(),
                doc.total_pages,
                ocr_text,
                f"{doc.avg_confidence:.2%}" if doc.avg_confidence else "N/A"
            ])
            
        AuditLog.objects.create(
            user=request.user, action=AuditLog.Action.EXPORT,
            resource_type='batch', resource_id=batch.id,
            details={'format': 'csv', 'documents_count': documents.count()}
        )

        return response

# ============================================================================
# GESTION DES DOCUMENTS
# ============================================================================

class DocumentView(LoginRequiredMixin, DetailView):
    model = Document
    template_name = 'document/view.html'
    context_object_name = 'document'
    pk_url_kwarg = 'document_id'

    def get_queryset(self):
        # Pré-charger les données liées pour optimiser les requêtes
        return Document.objects.filter(batch__user=self.request.user).prefetch_related(
            'pages__ocr_results'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.object
        
        # Préparer les données de chaque page pour le JavaScript
        pages_data = []
        all_pages = document.pages.all().order_by('page_number')
        
        for page in all_pages:
            # Récupérer le meilleur résultat OCR pour cette page
            ocr_result = page.ocr_results.order_by('-confidence_score').first()
            
            pages_data.append({
                'page_number': page.page_number,
                'image_url': page.image_path.url, # URL de l'image de la page
                'ocr_text': ocr_result.raw_text if ocr_result else "Aucun texte OCR trouvé pour cette page.",
                'confidence': (ocr_result.confidence_score or 0) * 100,
            })
        
        # Convertir les données en JSON pour les passer au template
        context['pages_data_json'] = json.dumps(pages_data)
        
        # Calculer la confiance moyenne pour tout le document
        avg_confidence = OCRResult.objects.filter(page__in=all_pages).aggregate(
            avg_conf=Avg('confidence_score')
        )['avg_conf'] or 0
        context['average_confidence'] = avg_confidence * 100
        
        # Logique de navigation entre documents (inchangée)
        batch_documents = list(document.batch.documents.order_by('created_at'))
        try:
            current_index = batch_documents.index(document)
            context['current_index'] = current_index + 1
            context['total_documents'] = len(batch_documents)
            context['prev_document'] = batch_documents[current_index - 1] if current_index > 0 else None
            context['next_document'] = batch_documents[current_index + 1] if current_index < len(batch_documents) - 1 else None
        except ValueError:
            # Le document n'est pas dans la liste, gérer le cas
            context['current_index'] = 1
            context['total_documents'] = 1
            context['prev_document'] = None
            context['next_document'] = None

        return context
class DocumentPreviewView(LoginRequiredMixin, DetailView):
    model = Document
    template_name = 'document/preview.html'
    context_object_name = 'document'
    pk_url_kwarg = 'document_id'

    def get_queryset(self):
        return Document.objects.filter(batch__user=self.request.user)

class DocumentValidateView(LoginRequiredMixin, View):
    def post(self, request, document_id):
        document = get_object_or_404(Document, id=document_id, batch__user=request.user)
        
        # Marquer le document comme validé
        document.status = Document.Status.VALIDATED
        document.save()
        
        # Marquer toutes les pages comme validées
        document.pages.update(status=Page.Status.VALIDATED)
        
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.VALIDATION_COMPLETE,
            resource_type='document',
            resource_id=document_id,
            details={'filename': document.original_filename}
        )
        
        return JsonResponse({'success': True, 'message': 'Document validé'})

class DocumentFlagView(LoginRequiredMixin, View):
    def post(self, request, document_id):
        document = get_object_or_404(Document, id=document_id, batch__user=request.user)
        reason = request.POST.get('reason', '')
        
        # Marquer le document comme problématique
        document.status = Document.Status.FAILED
        document.metadata['flag_reason'] = reason
        document.save()
        
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.ERROR,
            resource_type='document',
            resource_id=document_id,
            details={'reason': reason, 'filename': document.original_filename}
        )
        
        return JsonResponse({'success': True, 'message': 'Document signalé'})

class DocumentSaveView(LoginRequiredMixin, View):
    def post(self, request, document_id):
        document = get_object_or_404(Document, id=document_id, batch__user=request.user)
        annotations = json.loads(request.POST.get('annotations', '[]'))
        
        # Sauvegarder les annotations
        for annotation_data in annotations:
            page_id = annotation_data.get('page_id')
            if page_id:
                page = get_object_or_404(Page, id=page_id, document=document)
                Annotation.objects.create(
                    page=page,
                    user=request.user,
                    annotation_type=annotation_data.get('type', Annotation.Type.CORRECTION),
                    original_text=annotation_data.get('original_text', ''),
                    corrected_text=annotation_data.get('corrected_text', ''),
                    field_name=annotation_data.get('field_name', ''),
                    field_value=annotation_data.get('field_value', ''),
                    bounding_box=annotation_data.get('bounding_box', {}),
                    comment=annotation_data.get('comment', '')
                )
        
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            resource_type='document',
            resource_id=document_id,
            details={'annotations_count': len(annotations)}
        )
        
        return JsonResponse({'success': True, 'message': 'Modifications sauvegardées'})

class DocumentAssignView(LoginRequiredMixin, View):
    def post(self, request, document_id):
        document = get_object_or_404(Document, id=document_id, batch__user=request.user)
        user_id = request.POST.get('user_id')
        
        try:
            assignee = Utilisateur.objects.get(id=user_id, organization=request.user.organization)
            document.metadata['assigned_to'] = str(assignee.id)
            document.metadata['assigned_at'] = timezone.now().isoformat()
            document.save()
            
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.UPDATE,
                resource_type='document',
                resource_id=document_id,
                details={'assigned_to': str(assignee.id), 'assignee_name': assignee.get_full_name()}
            )
            
            return JsonResponse({'success': True, 'message': 'Document assigné'})
        except Utilisateur.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Utilisateur non trouvé'}, status=400)

class DocumentReprocessView(LoginRequiredMixin, View):
    def post(self, request, document_id):
        document = get_object_or_404(Document, id=document_id, batch__user=request.user)
        
        # Réinitialiser le statut des pages
        document.pages.update(status=Page.Status.OCR_PENDING)
        document.status = Document.Status.UPLOADED
        document.save()
        
        # Relancer le traitement OCR pour ce document
        # (À intégrer avec les tâches Celery)
        
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            resource_type='document',
            resource_id=document_id,
            details={'action': 'reprocess'}
        )
        
        return JsonResponse({'success': True, 'message': 'Retraitement lancé'})

class DocumentDeleteView(LoginRequiredMixin, View):
    def delete(self, request, document_id):
        document = get_object_or_404(Document, id=document_id, batch__user=request.user)
        document_name = document.original_filename
        document.delete()
        
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.DELETE,
            resource_type='document',
            resource_id=document_id,
            details={'filename': document_name}
        )
        
        return JsonResponse({'success': True, 'message': 'Document supprimé'})

class DocumentExportView(LoginRequiredMixin, View):
    def get(self, request, document_id):
        document = get_object_or_404(Document, id=document_id, batch__user=request.user)
        
        # Logique d'export à implémenter
        # Pour l'instant, retourner une réponse JSON
        data = {
            'id': str(document.id),
            'filename': document.original_filename,
            'status': document.status,
            'pages': document.pages.count(),
            'created_at': document.created_at.isoformat(),
        }
        
        return JsonResponse(data)

# ============================================================================
# ACTIONS EN LOT
# ============================================================================

class DocumentsBulkAssignView(LoginRequiredMixin, View):
    def post(self, request):
        document_ids = request.POST.getlist('document_ids')
        user_id = request.POST.get('user_id')
        
        try:
            assignee = Utilisateur.objects.get(id=user_id, organization=request.user.organization)
            documents = Document.objects.filter(id__in=document_ids, batch__user=request.user)
            
            for document in documents:
                document.metadata['assigned_to'] = str(assignee.id)
                document.metadata['assigned_at'] = timezone.now().isoformat()
                document.save()
            
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.UPDATE,
                resource_type='batch',
                resource_id='multiple',
                details={
                    'action': 'bulk_assign',
                    'documents_count': len(documents),
                    'assigned_to': str(assignee.id),
                    'assignee_name': assignee.get_full_name()
                }
            )
            
            return JsonResponse({'success': True, 'message': f'{len(documents)} documents assignés'})
        except Utilisateur.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Utilisateur non trouvé'}, status=400)

class DocumentsBulkValidateView(LoginRequiredMixin, View):
    def post(self, request):
        document_ids = request.POST.getlist('document_ids')
        documents = Document.objects.filter(id__in=document_ids, batch__user=request.user)
        
        for document in documents:
            document.status = Document.Status.VALIDATED
            document.save()
            document.pages.update(status=Page.Status.VALIDATED)
        
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.VALIDATION_COMPLETE,
            resource_type='batch',
            resource_id='multiple',
            details={
                'action': 'bulk_validate',
                'documents_count': len(documents)
            }
        )
        
        return JsonResponse({'success': True, 'message': f'{len(documents)} documents validés'})

class DocumentsBulkFlagView(LoginRequiredMixin, View):
    def post(self, request):
        document_ids = request.POST.getlist('document_ids')
        reason = request.POST.get('reason', 'Problème non spécifié')
        documents = Document.objects.filter(id__in=document_ids, batch__user=request.user)
        
        for document in documents:
            document.status = Document.Status.FAILED
            document.metadata['flag_reason'] = reason
            document.save()
        
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.ERROR,
            resource_type='batch',
            resource_id='multiple',
            details={
                'action': 'bulk_flag',
                'documents_count': len(documents),
                'reason': reason
            }
        )
        
        return JsonResponse({'success': True, 'message': f'{len(documents)} documents signalés'})

# ============================================================================
# FILE DE VALIDATION
# ============================================================================

class ValidationQueueView(LoginRequiredMixin, TemplateView):
    template_name = 'validation/queue.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Documents en attente de validation
        pending_documents = Document.objects.filter(
            batch__user=user,
            status=Document.Status.VALIDATION_PENDING
        )
        
        # Pages en attente de validation
        pending_pages = Page.objects.filter(
            document__batch__user=user,
            status=Page.Status.VALIDATION_PENDING
        )
        
        # Statistiques
        context['stats'] = {
            'pending_validation': pending_documents.count(),
            'validated_today': Document.objects.filter(
                batch__user=user,
                status=Document.Status.VALIDATED,
                updated_at__date=timezone.now().date()
            ).count(),
            'low_confidence': Page.objects.filter(
                document__batch__user=user,
                ocr_results__confidence_score__lt=0.7,
                status=Page.Status.VALIDATION_PENDING
            ).distinct().count(),
            'assigned_to_me': Document.objects.filter(
                batch__user=user,
                metadata__assigned_to=str(user.id),
                status=Document.Status.VALIDATION_PENDING
            ).count(),
        }
        
        # Documents pour la file d'attente
        context['documents'] = pending_documents.order_by('created_at')[:50]
        
        # Validateurs disponibles
        context['validators'] = Utilisateur.objects.filter(
            organization=user.organization,
            role__in=[Utilisateur.Role.VALIDATOR, Utilisateur.Role.ADMIN, Utilisateur.Role.SUPER_ADMIN]
        )
        
        # Lots avec documents en attente
        context['batches'] = Batch.objects.filter(
            user=user,
            documents__status=Document.Status.VALIDATION_PENDING
        ).distinct()
        
        return context

class ValidationCheckNewView(LoginRequiredMixin, View):
    def get(self, request):
        user = self.request.user
        last_check = request.GET.get('last_check')
        
        if last_check:
            try:
                last_check_dt = timezone.datetime.fromisoformat(last_check)
                new_count = Document.objects.filter(
                    batch__user=user,
                    status=Document.Status.VALIDATION_PENDING,
                    created_at__gt=last_check_dt
                ).count()
            except (ValueError, TypeError):
                new_count = 0
        else:
            new_count = Document.objects.filter(
                batch__user=user,
                status=Document.Status.VALIDATION_PENDING
            ).count()
        
        return JsonResponse({'has_new': new_count > 0, 'new_count': new_count})

# ============================================================================
# ADMINISTRATION
# ============================================================================

class AdminUsersView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'admin/users.html'
    model = Utilisateur
    context_object_name = 'users'
    
    def test_func(self):
        return self.request.user.is_org_admin
    
    def get_queryset(self):
        return Utilisateur.objects.filter(organization=self.request.user.organization)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['stats'] = {
            'total_users': self.get_queryset().count(),
            'active_users': self.get_queryset().filter(is_active=True).count(),
            'inactive_users': self.get_queryset().filter(is_active=False).count(),
            'admin_users': self.get_queryset().filter(role__in=[Utilisateur.Role.ADMIN, Utilisateur.Role.SUPER_ADMIN]).count(),
        }
        
        return context

class AdminUserDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Utilisateur
    template_name = 'admin/user_detail.html'
    context_object_name = 'user_detail'
    pk_url_kwarg = 'user_id'
    
    def test_func(self):
        return self.request.user.is_org_admin
    
    def get_queryset(self):
        return Utilisateur.objects.filter(organization=self.request.user.organization)

class AdminUserCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_org_admin
    
    def post(self, request):
        # Logique de création d'utilisateur
        # À implémenter selon vos besoins
        return JsonResponse({'success': True, 'message': 'Utilisateur créé'})

class AdminUserUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_org_admin
    
    def put(self, request, user_id):
        # Logique de modification d'utilisateur
        # À implémenter selon vos besoins
        return JsonResponse({'success': True, 'message': 'Utilisateur modifié'})

class AdminUserToggleView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_org_admin
    
    def post(self, request, user_id):
        user = get_object_or_404(Utilisateur, id=user_id, organization=request.user.organization)
        user.is_active = not user.is_active
        user.save()
        
        action = 'activé' if user.is_active else 'désactivé'
        return JsonResponse({'success': True, 'message': f'Utilisateur {action}'})

class AdminUserDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_org_admin
    
    def delete(self, request, user_id):
        user = get_object_or_404(Utilisateur, id=user_id, organization=request.user.organization)
        if user == request.user:
            return JsonResponse({'success': False, 'message': 'Vous ne pouvez pas supprimer votre propre compte'}, status=400)
        
        user.delete()
        return JsonResponse({'success': True, 'message': 'Utilisateur supprimé'})

class AdminUsersExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_org_admin
    
    def get(self, request):
        # Logique d'export des utilisateurs
        # À implémenter selon vos besoins
        return HttpResponse('Export utilisateurs', content_type='text/csv')

class AdminOrganizationsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'admin/organizations.html'
    
    def test_func(self):
        return self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organizations'] = Organization.objects.all()
        return context

class AdminAPIKeysView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'admin/api_keys.html'
    model = APIKey
    context_object_name = 'api_keys'
    
    def test_func(self):
        return self.request.user.is_org_admin
    
    def get_queryset(self):
        return APIKey.objects.filter(organization=self.request.user.organization)

class AdminSettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'admin/settings.html'
    
    def test_func(self):
        return self.request.user.is_org_admin

# ============================================================================
# ARCHIVES ET HISTORIQUE
# ============================================================================

class ArchiveHistoryView(LoginRequiredMixin, ListView):
    template_name = 'archive/history.html'
    model = AuditLog
    context_object_name = 'activities'
    paginate_by = 20
    
    def get_queryset(self):
        return AuditLog.objects.filter(user=self.request.user).order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Statistiques
        user_batches = Batch.objects.filter(user=user)
        context['stats'] = {
            'total_documents': Document.objects.filter(batch__in=user_batches).count(),
            'total_batches': user_batches.count(),
            'total_exports': ExportProfile.objects.filter(organization=user.organization).count(),
            'storage_used': Document.objects.filter(batch__in=user_batches).aggregate(total_size=Sum('file_size'))['total_size'] or 0,
        }
        
        # Utilisateurs pour les filtres
        context['users'] = Utilisateur.objects.filter(organization=user.organization)
        
        return context

class ArchiveExportView(LoginRequiredMixin, View):
    def post(self, request):
        # Logique d'export des archives
        # À implémenter selon vos besoins
        return HttpResponse('Export archives', content_type='application/octet-stream')

class ActivityDetailsView(LoginRequiredMixin, View):
    def get(self, request, activity_id):
        activity = get_object_or_404(AuditLog, id=activity_id, user=request.user)
        
        details_html = f"""
        <div class="activity-details">
            <h4>Détails de l'activité</h4>
            <p><strong>Action:</strong> {activity.get_action_display()}</p>
            <p><strong>Ressource:</strong> {activity.resource_type} {activity.resource_id}</p>
            <p><strong>Date:</strong> {activity.timestamp}</p>
            <p><strong>Détails:</strong> {json.dumps(activity.details, indent=2)}</p>
        </div>
        """
        
        return JsonResponse({
            'success': True,
            'html': details_html
        })

class ArchiveCheckNewView(LoginRequiredMixin, View):
    def get(self, request):
        user = self.request.user
        last_check = request.GET.get('last_check')
        
        if last_check:
            try:
                last_check_dt = timezone.datetime.fromisoformat(last_check)
                new_activities = AuditLog.objects.filter(
                    user=user,
                    timestamp__gt=last_check_dt
                ).exists()
            except (ValueError, TypeError):
                new_activities = False
        else:
            new_activities = AuditLog.objects.filter(user=user).exists()
        
        latest_id = AuditLog.objects.filter(user=user).order_by('-timestamp').first()
        latest_id = str(latest_id.id) if latest_id else None
        
        return JsonResponse({'has_new': new_activities, 'latest_id': latest_id})

# ============================================================================
# PROFIL UTILISATEUR
# ============================================================================

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Statistiques de l'utilisateur
        user_batches = Batch.objects.filter(user=user)
        context['user_stats'] = {
            'total_batches': user_batches.count(),
            'total_documents': Document.objects.filter(batch__in=user_batches).count(),
            'documents_validated': Document.objects.filter(batch__in=user_batches, status=Document.Status.VALIDATED).count(),
            'last_activity': user.last_activity,
        }
        
        return context

class UserSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'profile/settings.html'

# ============================================================================
# API ENDPOINTS
# ============================================================================

class BatchStatusAPIView(LoginRequiredMixin, View):
    def get(self, request, batch_id):
        batch = get_object_or_404(Batch, id=batch_id, user=request.user)
        return JsonResponse({
            'status': batch.status,
            'progress': batch.progress_percentage,
            'processed_documents': batch.processed_documents,
            'total_documents': batch.total_documents
        })

class DocumentConfidenceAPIView(LoginRequiredMixin, View):
    def get(self, request, document_id):
        document = get_object_or_404(Document, id=document_id, batch__user=request.user)
        
        # Calculer la confiance moyenne des résultats OCR du document
        avg_confidence = OCRResult.objects.filter(
            page__document=document
        ).aggregate(avg_conf=Avg('confidence_score'))['avg_conf'] or 0
        
        return JsonResponse({'confidence': round(avg_confidence * 100, 2)})

class DashboardStatsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        user_batches = Batch.objects.filter(user=user)
        
        stats = {
            'total_batches': user_batches.count(),
            'total_documents': Document.objects.filter(batch__in=user_batches).count(),
            'pending_validation': Document.objects.filter(
                batch__in=user_batches, 
                status=Document.Status.VALIDATION_PENDING
            ).count(),
            'accuracy_rate': round((
                OCRResult.objects.filter(
                    page__document__batch__in=user_batches
                ).aggregate(avg_conf=Avg('confidence_score'))['avg_conf'] or 0
            ) * 100, 2),
        }
        
        return JsonResponse(stats)

class NotificationsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        
        # Notifications (exemples)
        notifications = [
            {
                'id': 1,
                'type': 'info',
                'message': 'Votre lot "Factures Q4" est terminé',
                'timestamp': timezone.now().isoformat(),
                'read': False
            }
        ]
        
        return JsonResponse({'notifications': notifications})

# ============================================================================
# PAGES D'ERREUR PERSONNALISÉES
# ============================================================================

def custom_404(request, exception):
    return render(request, 'errors/404.html', status=404)

def custom_500(request):
    return render(request, 'errors/500.html', status=500)