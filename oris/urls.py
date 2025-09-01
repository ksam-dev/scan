"""
URLs pour l'API ORIS
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'organizations', views.OrganizationViewSet)
router.register(r'batches', views.BatchViewSet, basename='batch')
router.register(r'documents', views.DocumentViewSet, basename='document')
router.register(r'pages', views.PageViewSet, basename='page')
router.register(r'ocr-results', views.OCRResultViewSet, basename='ocrresult')
router.register(r'annotations', views.AnnotationViewSet, basename='annotation')
router.register(r'audit-logs', views.AuditLogViewSet, basename='auditlog')
router.register(r'handwriting-samples', views.HandwritingSampleViewSet, basename='handwritingsample')
router.register(r'validate', views.ValidationViewSet, basename='validation')

urlpatterns = [
    # API REST
    path('', include(router.urls)),
        # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Gestion des lots
    path('batch/upload/', views.BatchUploadView.as_view(), name='batch_upload'),
    path('batch/list/', views.BatchListView.as_view(), name='batch_list'),
    path('batch/<uuid:batch_id>/', views.BatchDetailView.as_view(), name='batch_detail'),
    path('batch/<uuid:batch_id>/delete/', views.BatchDeleteView.as_view(), name='batch_delete'),
    path('batch/<uuid:batch_id>/export/', views.BatchExportView.as_view(), name='batch_export'),

    # Gestion des documents
    path('document/<uuid:document_id>/view/', views.DocumentView.as_view(), name='document_view'),
    path('document/<uuid:document_id>/save/', views.DocumentSaveView.as_view(), name='document_save'),
    path('document/<uuid:document_id>/validate/', views.DocumentValidateView.as_view(), name='document_validate'),
    
    # File de validation
    path('validation/queue/', views.ValidationQueueView.as_view(), name='validation_queue'),
    
    # Archives
    path('archive/', views.ArchiveHistoryView.as_view(), name='archive'),
    
    # Administration (Exemple)
    path('admin/users/', views.AdminUsersView.as_view(), name='admin_users'),
    
    # Profil
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('settings/', views.UserSettingsView.as_view(), name='settings'), # Assurez-vous que cette URL existe

    # # Webhooks
    # path('webhooks/batch/<uuid:batch_id>/complete/', views.webhook_batch_complete, name='webhook_batch_complete'),
    # path('webhooks/document/<uuid:document_id>/complete/', views.webhook_document_complete, name='webhook_document_complete'),
]

