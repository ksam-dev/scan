"""
Configuration de l'admin Django pour ORIS
"""

from django.contrib import admin
from .models import (
    Organization, Batch, Document, Page, OCRResult, 
    Annotation, AuditLog, HandwritingSample
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0
    readonly_fields = ['id', 'file_size', 'total_pages', 'processed_pages', 'created_at']


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'user', 'status', 'total_documents', 'processed_documents', 'created_at']
    list_filter = ['status', 'organization', 'created_at']
    search_fields = ['name', 'user__username', 'organization__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [DocumentInline]


class PageInline(admin.TabularInline):
    model = Page
    extra = 0
    readonly_fields = ['id', 'page_number', 'status', 'is_handwritten', 'created_at']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'batch', 'document_type', 'status', 'total_pages', 'processed_pages', 'created_at']
    list_filter = ['document_type', 'status', 'created_at']
    search_fields = ['original_filename', 'batch__name']
    readonly_fields = ['id', 'file_size', 'created_at', 'updated_at']
    inlines = [PageInline]


class OCRResultInline(admin.TabularInline):
    model = OCRResult
    extra = 0
    readonly_fields = ['id', 'engine', 'confidence_score', 'processing_time', 'created_at']


class AnnotationInline(admin.TabularInline):
    model = Annotation
    extra = 0
    readonly_fields = ['id', 'user', 'annotation_type', 'created_at']


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'document', 'page_number', 'status', 'is_handwritten', 'created_at']
    list_filter = ['status', 'is_handwritten', 'created_at']
    search_fields = ['document__original_filename', 'document__batch__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [OCRResultInline, AnnotationInline]


@admin.register(OCRResult)
class OCRResultAdmin(admin.ModelAdmin):
    list_display = ['page', 'engine', 'confidence_score', 'processing_time', 'created_at']
    list_filter = ['engine', 'created_at']
    search_fields = ['page__document__original_filename', 'raw_text']
    readonly_fields = ['id', 'created_at']


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ['page', 'user', 'annotation_type', 'field_name', 'created_at']
    list_filter = ['annotation_type', 'created_at']
    search_fields = ['page__document__original_filename', 'user__username', 'original_text', 'corrected_text']
    readonly_fields = ['id', 'created_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'resource_type', 'resource_id', 'timestamp']
    list_filter = ['action', 'resource_type', 'timestamp']
    search_fields = ['user__username', 'resource_id']
    readonly_fields = ['id', 'timestamp']


@admin.register(HandwritingSample)
class HandwritingSampleAdmin(admin.ModelAdmin):
    list_display = ['page', 'language', 'writing_style', 'quality_score', 'used_for_training', 'created_at']
    list_filter = ['language', 'used_for_training', 'created_at']
    search_fields = ['page__document__original_filename', 'ground_truth_text']
    readonly_fields = ['id', 'created_at']
