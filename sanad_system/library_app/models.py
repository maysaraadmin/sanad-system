from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
import os
from django.utils.text import slugify

def upload_to(instance, filename):
    # File will be uploaded to MEDIA_ROOT/library/<document_type>/<year>/<filename>
    # Use current year if instance is not saved yet
    from datetime import datetime
    year = datetime.now().year if instance.uploaded_at is None else instance.uploaded_at.year
    document_type = instance.document_type
    filename = f"{slugify(instance.title)}_{os.path.splitext(filename)[0]}{os.path.splitext(filename)[1]}"
    return f'library/{document_type}/{year}/{filename}'

class DocumentType(models.Model):
    """Document types for categorization"""
    name = models.CharField(max_length=50, verbose_name="نوع المستند")
    description = models.TextField(null=True, blank=True, verbose_name="الوصف")
    
    class Meta:
        verbose_name = "نوع المستند"
        verbose_name_plural = "أنواع المستندات"
        ordering = ['name']
        
    def __str__(self):
        return self.name

class Document(models.Model):
    """Model for uploaded documents"""
    title = models.CharField(max_length=200, verbose_name="العنوان")
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.CASCADE,
        verbose_name="نوع المستند"
    )
    file = models.FileField(
        upload_to=upload_to,
        verbose_name="الملف"
    )
    description = models.TextField(null=True, blank=True, verbose_name="الوصف")
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="تم رفعه بواسطة"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الرفع")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ آخر تحديث")
    is_public = models.BooleanField(default=True, verbose_name="عام")
    
    class Meta:
        verbose_name = "مستند"
        verbose_name_plural = "المستندات"
        ordering = ['-uploaded_at']
        
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('library_app:document_detail', kwargs={'pk': self.pk})
    
    @property
    def file_size(self):
        """Return file size in a human-readable format"""
        size = self.file.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
