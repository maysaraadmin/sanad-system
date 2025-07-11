from django.contrib import admin
from .models import Document, DocumentType

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    ordering = ('name',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'document_type', 'uploaded_by', 'uploaded_at', 'is_public')
    list_filter = ('document_type', 'is_public', 'uploaded_at')
    search_fields = ('title', 'description', 'uploaded_by__username')
    ordering = ('-uploaded_at',)
    readonly_fields = ('uploaded_at', 'updated_at')
