from django.contrib import admin
from .models import DocumentAnalysis

@admin.register(DocumentAnalysis)
class DocumentAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'document')
    readonly_fields = ('created_at', 'updated_at', 'result', 'error_message')