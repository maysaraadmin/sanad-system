from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Document, DocumentCategory

@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'document_count', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)
    prepopulated_fields = {}
    
    def document_count(self, obj):
        return obj.document_set.count()
    document_count.short_description = _('عدد المستندات')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'file_type', 'category', 'uploaded_by', 'created_at', 'is_public')
    list_filter = ('file_type', 'category', 'is_public', 'created_at')
    search_fields = ('title', 'description')
    list_editable = ('is_public',)
    readonly_fields = ('created_at', 'updated_at', 'file_type')
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'file', 'file_type', 'category')
        }),
        (_('الإعدادات'), {
            'fields': ('is_public', 'uploaded_by')
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set the uploaded_by field if this is a new object
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

    class Media:
        js = (
            '//cdnjs.cloudflare.com/ajax/libs/pdf.js/2.11.338/pdf.min.js',
            'library/js/admin_preview.js',
        )
