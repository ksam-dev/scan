# ORIS - Système OCR - Configuration des URLs

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

# Vues principales
from oris import views

urlpatterns = [
    # Administration Django
    path('admin/', admin.site.urls),
    
    # Authentification
    path('', views.LoginView.as_view(), name='login'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='auth/password_reset.html',
        email_template_name='auth/password_reset_email.html',
        subject_template_name='auth/password_reset_subject.txt',
        success_url='/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='auth/password_reset_done.html'
    ), name='password_reset_done'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Gestion des lots
    path('batch/', include([
        path('upload/', views.BatchUploadView.as_view(), name='batch_upload'),
        path('list/', views.BatchListView.as_view(), name='batch_list'),
        
        # CORRECTION ICI : Capturer l'ID du lot qui est un UUID
        path('<uuid:batch_id>/', views.BatchDetailView.as_view(), name='batch_detail'),
        path('<uuid:batch_id>/reprocess/', views.BatchReprocessView.as_view(), name='batch_reprocess'),
        path('<uuid:batch_id>/delete/', views.BatchDeleteView.as_view(), name='batch_delete'),
        path('<uuid:batch_id>/export/', views.BatchExportView.as_view(), name='batch_export'),
    ])),
    
    # Gestion des documents
    path('document/', include([
        path('<uuid:document_id>/view/', views.DocumentView.as_view(), name='document_view'),
        path('<int:document_id>/preview/', views.DocumentPreviewView.as_view(), name='document_preview'),
        path('<int:document_id>/validate/', views.DocumentValidateView.as_view(), name='document_validate'),
        path('<int:document_id>/flag/', views.DocumentFlagView.as_view(), name='document_flag'),
        path('<int:document_id>/save/', views.DocumentSaveView.as_view(), name='document_save'),
        path('<int:document_id>/assign/', views.DocumentAssignView.as_view(), name='document_assign'),
        path('<int:document_id>/reprocess/', views.DocumentReprocessView.as_view(), name='document_reprocess'),
        path('<int:document_id>/delete/', views.DocumentDeleteView.as_view(), name='document_delete'),
        path('<int:document_id>/export/', views.DocumentExportView.as_view(), name='document_export'),
    ])),
    
    # Actions en lot sur les documents
    path('documents/', include([
        path('bulk-assign/', views.DocumentsBulkAssignView.as_view(), name='documents_bulk_assign'),
        path('bulk-validate/', views.DocumentsBulkValidateView.as_view(), name='documents_bulk_validate'),
        path('bulk-flag/', views.DocumentsBulkFlagView.as_view(), name='documents_bulk_flag'),
    ])),
    
    # File de validation
    path('validation/', include([
        path('queue/', views.ValidationQueueView.as_view(), name='validation_queue'),
        path('check-new/', views.ValidationCheckNewView.as_view(), name='validation_check_new'),
    ])),
    
    # Administration
    path('admin-panel/', include([
        path('users/', views.AdminUsersView.as_view(), name='admin_users'),
        path('users/<int:user_id>/', views.AdminUserDetailView.as_view(), name='admin_user_detail'),
        path('users/create/', views.AdminUserCreateView.as_view(), name='admin_user_create'),
        path('users/<int:user_id>/update/', views.AdminUserUpdateView.as_view(), name='admin_user_update'),
        path('users/<int:user_id>/toggle/', views.AdminUserToggleView.as_view(), name='admin_user_toggle'),
        path('users/<int:user_id>/delete/', views.AdminUserDeleteView.as_view(), name='admin_user_delete'),
        path('users/export/', views.AdminUsersExportView.as_view(), name='admin_users_export'),
        path('organizations/', views.AdminOrganizationsView.as_view(), name='admin_organizations'),
        path('api-keys/', views.AdminAPIKeysView.as_view(), name='admin_api_keys'),
        path('settings/', views.AdminSettingsView.as_view(), name='admin_settings'),
    ])),
    
    # Archives et historique
    path('archive/', include([
        path('', views.ArchiveHistoryView.as_view(), name='archive'),
        path('export/', views.ArchiveExportView.as_view(), name='archive_export'),
        path('activity/<int:activity_id>/details/', views.ActivityDetailsView.as_view(), name='activity_details'),
        path('check-new/', views.ArchiveCheckNewView.as_view(), name='archive_check_new'),
    ])),
    
    # Profil utilisateur
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('settings/', views.UserSettingsView.as_view(), name='settings'),
    
    # API endpoints (pour HTMX et AJAX)
    path('api/', include([
        path('batch/<int:batch_id>/status/', views.BatchStatusAPIView.as_view(), name='api_batch_status'),
        path('document/<int:document_id>/confidence/', views.DocumentConfidenceAPIView.as_view(), name='api_document_confidence'),
        path('stats/dashboard/', views.DashboardStatsAPIView.as_view(), name='api_dashboard_stats'),
        path('notifications/', views.NotificationsAPIView.as_view(), name='api_notifications'),
    ])),
]

# Configuration pour servir les fichiers media en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Configuration des pages d'erreur personnalisées
handler404 = 'oris.views.custom_404'
handler500 = 'oris.views.custom_500'

