from django.contrib import admin
from .models import Document
from django.utils.html import format_html
from django.urls import reverse

class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_by', 'uploaded_at', 'file_size_display', 'page_count', 'is_public')
    list_filter = ('is_public', 'uploaded_at')
    search_fields = ('title', 'description')
    readonly_fields = ('uploaded_at', 'file_size', 'page_count')
    fieldsets = (
        ('معلومات المستند', {
            'fields': ('title', 'description', 'file', 'is_public')
        }),
        ('معلومات إضافية', {
            'classes': ('collapse',),
            'fields': ('uploaded_by', 'uploaded_at', 'file_size', 'page_count'),
        }),
    )
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"
    file_size_display.short_description = 'حجم الملف'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set added_by during the first save.
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

admin.site.register(Document, DocumentAdmin)
