from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import os

def document_upload_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/documents/<category_name>/<filename>
    ext = filename.split('.')[-1]
    filename = f"{instance.title}.{ext}"
    # Use category name if category exists, otherwise use 'uncategorized'
    category_dir = instance.category.name if instance.category else 'uncategorized'
    # Clean the category name to be filesystem-safe
    import re
    category_dir = re.sub(r'[^\w\-]', '_', category_dir.lower())
    return os.path.join('documents', category_dir, filename)

class DocumentCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("اسم التصنيف"))
    description = models.TextField(blank=True, null=True, verbose_name=_("الوصف"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("تصنيف المستندات")
        verbose_name_plural = _("تصنيفات المستندات")
        ordering = ['name']

    def __str__(self):
        return self.name

class Document(models.Model):
    DOCUMENT_TYPES = (
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('other', 'Other'),
    )

    title = models.CharField(max_length=200, verbose_name=_("العنوان"))
    description = models.TextField(blank=True, null=True, verbose_name=_("الوصف"))
    file = models.FileField(upload_to=document_upload_path, verbose_name=_("الملف"))
    file_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES, verbose_name=_("نوع الملف"))
    category = models.ForeignKey(DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("التصنيف"))
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name=_("تم الرفع بواسطة"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الرفع"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))
    is_public = models.BooleanField(default=True, verbose_name=_("متاح للعامة"))

    class Meta:
        verbose_name = _("مستند")
        verbose_name_plural = _("المستندات")
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('library:document_detail', kwargs={'pk': self.id})

    def get_file_extension(self):
        name, extension = os.path.splitext(self.file.name)
        return extension[1:].lower()

    def save(self, *args, **kwargs):
        # Set the file type based on the file extension
        if not self.file_type:
            ext = self.get_file_extension()
            if ext == 'pdf':
                self.file_type = 'pdf'
            elif ext in ['doc', 'docx']:
                self.file_type = 'docx'
            else:
                self.file_type = 'other'
        super().save(*args, **kwargs)
