from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import RAGQuery, DocumentEmbedding, RAGConfiguration


@admin.register(RAGQuery)
class RAGQueryAdmin(admin.ModelAdmin):
    """Admin interface for RAG queries"""
    list_display = ['query', 'user', 'created_at', 'embedding_model', 'llm_model']
    list_filter = ['embedding_model', 'llm_model', 'created_at', 'user']
    search_fields = ['query', 'response']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'query', 'response')
        }),
        (_('Technical Details'), {
            'fields': ('embedding_model', 'llm_model', 'context_used'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers can only see their own queries
            qs = qs.filter(user=request.user)
        return qs


@admin.register(DocumentEmbedding)
class DocumentEmbeddingAdmin(admin.ModelAdmin):
    """Admin interface for document embeddings"""
    list_display = ['content_type', 'content_id', 'embedding_model', 'created_at']
    list_filter = ['content_type', 'embedding_model', 'created_at']
    search_fields = ['text_content']
    readonly_fields = ['id', 'created_at', 'updated_at', 'embedding_vector']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('content_type', 'content_id', 'text_content')
        }),
        (_('Technical Details'), {
            'fields': ('embedding_model', 'metadata'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        (_('Embedding Vector'), {
            'fields': ('embedding_vector',),
            'classes': ('collapse',),
            'description': _('Raw embedding vector data (read-only)')
        }),
    )
    
    def has_add_permission(self, request):
        # Prevent manual addition of embeddings through admin
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        # Only superusers can modify embeddings
        return request.user.is_superuser


@admin.register(RAGConfiguration)
class RAGConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for RAG configurations"""
    list_display = ['name', 'embedding_model', 'llm_model', 'is_active', 'created_at']
    list_filter = ['is_active', 'embedding_model', 'llm_model', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        (_('Model Configuration'), {
            'fields': ('embedding_model', 'llm_model')
        }),
        (_('Processing Parameters'), {
            'fields': ('chunk_size', 'chunk_overlap', 'max_context', 'similarity_threshold')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_configuration', 'deactivate_configuration']
    
    def activate_configuration(self, request, queryset):
        """Activate selected configuration and deactivate others"""
        if queryset.count() > 1:
            self.message_user(request, _('You can only activate one configuration at a time.'), level='error')
            return
        
        config = queryset.first()
        # Deactivate all other configurations
        RAGConfiguration.objects.exclude(pk=config.pk).update(is_active=False)
        # Activate the selected one
        config.is_active = True
        config.save()
        
        self.message_user(request, _(f'Configuration "{config.name}" has been activated.'))
    activate_configuration.short_description = _('Activate configuration (deactivates others)')
    
    def deactivate_configuration(self, request, queryset):
        """Deactivate selected configurations"""
        count = queryset.update(is_active=False)
        self.message_user(request, _(f'{count} configuration(s) have been deactivated.'))
    deactivate_configuration.short_description = _('Deactivate configurations')


# Customize admin site headers
admin.site.site_header = _('نظام السند - RAG Management')
admin.site.site_title = _('RAG Admin')
admin.site.index_title = _('Welcome to RAG System Administration')
