# ORIS - Système OCR - Vues Django Étendues

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView, View
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import User
import json
import csv
from datetime import datetime, timedelta

# Données factices étendues
MOCK_STATS = {
    'total_batches': 156,
    'pending_validation': 23,
    'documents_processed': 2847,
    'accuracy_rate': 94.2,
    'total_organizations': 12,
    'active_organizations': 10,
    'inactive_organizations': 2,
    'total_users_in_orgs': 45,
    'total_keys': 8,
    'active_keys': 6,
    'inactive_keys': 2,
    'total_requests': 15420,
}

MOCK_ORGANIZATIONS = [
    {
        'id': 1,
        'name': 'Entreprise ABC',
        'location': 'Paris, France',
        'user_count': 15,
        'document_count': 450,
        'is_active': True,
        'created_at': timezone.now() - timedelta(days=30),
        'contact_email': 'admin@abc.com',
        'logo_url': None,
    },
    {
        'id': 2,
        'name': 'Société XYZ',
        'location': 'Lyon, France',
        'user_count': 8,
        'document_count': 230,
        'is_active': True,
        'created_at': timezone.now() - timedelta(days=15),
        'contact_email': 'contact@xyz.com',
        'logo_url': None,
    },
]

MOCK_API_KEYS = [
    {
        'id': 1,
        'name': 'API Production',
        'key_value': 'oris_prod_1234567890abcdef',
        'created_by': {'username': 'admin', 'get_full_name': lambda: 'Administrateur'},
        'created_at': timezone.now() - timedelta(days=10),
        'is_active': True,
        'request_count': 8520,
        'permissions': ['read:documents', 'write:batches'],
    },
    {
        'id': 2,
        'name': 'API Test',
        'key_value': 'oris_test_abcdef1234567890',
        'created_by': {'username': 'developer', 'get_full_name': lambda: 'Développeur'},
        'created_at': timezone.now() - timedelta(days=5),
        'is_active': False,
        'request_count': 150,
        'permissions': ['read:documents'],
    },
]

MOCK_ACTIVITIES = [
    {
        'id': 1,
        'title': 'Lot "Factures Q4" traité avec succès',
        'icon': 'check-circle',
        'created_at': timezone.now() - timedelta(hours=2),
    },
    {
        'id': 2,
        'title': 'Nouveau document ajouté à la validation',
        'icon': 'file-alt',
        'created_at': timezone.now() - timedelta(hours=5),
    },
    {
        'id': 3,
        'title': 'Utilisateur "Jean Dupont" créé',
        'icon': 'user-plus',
        'created_at': timezone.now() - timedelta(days=1),
    },
]

# Administration - Organisations
class AdminOrganizationsView(LoginRequiredMixin, TemplateView):
    template_name = 'admin/organizations.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organizations'] = MOCK_ORGANIZATIONS
        context['stats'] = MOCK_STATS
        return context

class AdminOrganizationDetailView(LoginRequiredMixin, View):
    def get(self, request, org_id):
        org = next((o for o in MOCK_ORGANIZATIONS if o['id'] == org_id), None)
        if org:
            return JsonResponse({'success': True, 'organization': org})
        return JsonResponse({'success': False, 'message': 'Organisation non trouvée'})

class AdminOrganizationCreateView(LoginRequiredMixin, View):
    def post(self, request):
        return JsonResponse({'success': True, 'message': 'Organisation créée'})

class AdminOrganizationUpdateView(LoginRequiredMixin, View):
    def put(self, request, org_id):
        return JsonResponse({'success': True, 'message': 'Organisation modifiée'})

class AdminOrganizationToggleView(LoginRequiredMixin, View):
    def post(self, request, org_id):
        return JsonResponse({'success': True, 'message': 'Statut modifié'})

class AdminOrganizationDeleteView(LoginRequiredMixin, View):
    def delete(self, request, org_id):
        return JsonResponse({'success': True, 'message': 'Organisation supprimée'})

class AdminOrganizationsExportView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="organizations.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'Location', 'Users', 'Documents', 'Active'])
        for org in MOCK_ORGANIZATIONS:
            writer.writerow([org['name'], org['location'], org['user_count'], org['document_count'], org['is_active']])
        
        return response

# Administration - Clés API
class AdminAPIKeysView(LoginRequiredMixin, TemplateView):
    template_name = 'admin/api_keys.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['api_keys'] = MOCK_API_KEYS
        context['users'] = User.objects.all()
        context['stats'] = MOCK_STATS
        return context

class AdminAPIKeyDetailView(LoginRequiredMixin, View):
    def get(self, request, key_id):
        key = next((k for k in MOCK_API_KEYS if k['id'] == key_id), None)
        if key:
            return JsonResponse({'success': True, 'api_key': key})
        return JsonResponse({'success': False, 'message': 'Clé API non trouvée'})

class AdminAPIKeyCreateView(LoginRequiredMixin, View):
    def post(self, request):
        return JsonResponse({'success': True, 'message': 'Clé API créée'})

class AdminAPIKeyUpdateView(LoginRequiredMixin, View):
    def put(self, request, key_id):
        return JsonResponse({'success': True, 'message': 'Clé API modifiée'})

class AdminAPIKeyToggleView(LoginRequiredMixin, View):
    def post(self, request, key_id):
        return JsonResponse({'success': True, 'message': 'Statut modifié'})

class AdminAPIKeyDeleteView(LoginRequiredMixin, View):
    def delete(self, request, key_id):
        return JsonResponse({'success': True, 'message': 'Clé API supprimée'})

class AdminAPIKeysExportView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="api_keys.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'Key', 'Created By', 'Active', 'Requests'])
        for key in MOCK_API_KEYS:
            writer.writerow([key['name'], key['key_value'], key['created_by']['username'], key['is_active'], key['request_count']])
        
        return response

# Administration - Paramètres système
class AdminSystemSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'admin/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = {
            'OCR_ENGINE': 'tesseract',
            'OCR_LANGUAGES': ['fra', 'eng'],
            'CONFIDENCE_THRESHOLD': 70,
            'MAX_FILE_SIZE_MB': 50,
            'ALLOWED_EXTENSIONS': ['.pdf', '.jpg', '.png', '.tiff'],
            'EMAIL_NOTIFICATIONS_ENABLED': True,
            'BROWSER_NOTIFICATIONS_ENABLED': True,
            'BATCH_COMPLETION_NOTIFY': True,
            'TWO_FACTOR_AUTH_ENABLED': False,
            'SESSION_TIMEOUT_MINUTES': 60,
        }
        return context

class AdminSettingsSaveView(LoginRequiredMixin, View):
    def post(self, request):
        return JsonResponse({'success': True, 'message': 'Paramètres sauvegardés'})

class AdminMaintenanceTaskView(LoginRequiredMixin, View):
    def post(self, request, task_name):
        messages = {
            'clean_old_data': '150 anciens enregistrements supprimés',
            'rebuild_index': 'Index de recherche reconstruit avec succès',
        }
        return JsonResponse({
            'success': True, 
            'message': messages.get(task_name, 'Tâche exécutée')
        })

# Profil utilisateur étendu
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_activities'] = MOCK_ACTIVITIES
        # Ajouter des attributs de profil factices
        context['user'].profile = type('Profile', (), {
            'documents_validated': 45,
            'batches_created': 12,
            'accuracy_rate': 92,
            'phone': '+33 1 23 45 67 89',
            'organization': 'Entreprise ABC',
            'bio': 'Spécialiste en validation de documents OCR',
            'email_notifications': True,
            'browser_notifications': True,
            'batch_completion_notify': True,
            'language': 'fr',
            'timezone': 'Europe/Paris',
            'password_changed_at': timezone.now() - timedelta(days=30),
        })()
        return context

class ProfileUpdateView(LoginRequiredMixin, View):
    def post(self, request):
        return JsonResponse({'success': True, 'message': 'Profil mis à jour'})

class ProfilePreferencesView(LoginRequiredMixin, View):
    def post(self, request):
        return JsonResponse({'success': True, 'message': 'Préférences sauvegardées'})

class ProfileUploadAvatarView(LoginRequiredMixin, View):
    def post(self, request):
        return JsonResponse({'success': True, 'message': 'Avatar mis à jour'})

class ProfileChangePasswordView(LoginRequiredMixin, TemplateView):
    template_name = 'profile/change_password.html'

# API endpoints étendues
class APIOrganizationsView(LoginRequiredMixin, View):
    def get(self, request):
        return JsonResponse({'organizations': MOCK_ORGANIZATIONS})

class APIKeysView(LoginRequiredMixin, View):
    def get(self, request):
        return JsonResponse({'api_keys': MOCK_API_KEYS})

