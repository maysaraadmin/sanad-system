# document_analysis/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator

User = get_user_model()

class DocumentAnalysis(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_analyses')
    document = models.FileField(
        upload_to='document_analyses/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        null=True,
        blank=True
    )
    library_document = models.ForeignKey(
        'library_app.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analyses'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Document Analyses'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Analysis {self.id} - {self.get_status_display()}"
    
    def get_document_name(self):
        if self.library_document:
            return self.library_document.title
        elif self.document:
            return self.document.name
        return 'No document'
    
    def get_document_url(self):
        if self.library_document:
            return self.library_document.file.url
        elif self.document:
            return self.document.url
        return None