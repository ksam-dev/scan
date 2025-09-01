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
    
    # Webhooks
    path('webhooks/batch/<uuid:batch_id>/complete/', views.webhook_batch_complete, name='webhook_batch_complete'),
    path('webhooks/document/<uuid:document_id>/complete/', views.webhook_document_complete, name='webhook_document_complete'),
]

