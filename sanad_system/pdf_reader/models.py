import os
import mimetypes
import fitz  # PyMuPDF
from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _

def document_upload_path(instance, filename):
    """Generate a unique file path for the uploaded document"""
    # Get the file extension
    ext = os.path.splitext(filename)[1].lower()
    # Create a safe filename
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    safe_filename = f"{slugify(instance.title)}_{timestamp}{ext}"
    return os.path.join('documents', safe_filename)

class DocumentQuerySet(models.QuerySet):
    """Custom QuerySet for Document model with common filters"""
    
    def public(self):
        """Return only public documents"""
        return self.filter(is_public=True)
    
    def by_user(self, user):
        """Return documents accessible by a specific user"""
        if user.is_staff:
            return self.all()
        return self.filter(Q(is_public=True) | Q(uploaded_by=user))
    
    def recent(self, days=30):
        """Return documents uploaded in the last N days"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(uploaded_at__gte=cutoff_date)

class DocumentManager(models.Manager):
    """Custom manager for Document model"""
    
    def get_queryset(self):
        return DocumentQuerySet(self.model, using=self._db)
    
    def public(self):
        return self.get_queryset().public()
    
    def by_user(self, user):
        return self.get_queryset().by_user(user)
    
    def recent(self, days=30):
        return self.get_queryset().recent(days)

class Document(models.Model):
    """Model representing a document in the library"""
    
    # Document status choices
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_DRAFT, _('مسودة')),
        (STATUS_PUBLISHED, _('منشور')),
        (STATUS_ARCHIVED, _('مؤرشف')),
    ]
    
    # Document type choices
    TYPE_PDF = 'pdf'
    TYPE_DOC = 'doc'
    TYPE_IMAGE = 'image'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_PDF, 'PDF'),
        (TYPE_DOC, 'وثيقة معالجة النصوص'),
        (TYPE_IMAGE, 'صورة'),
        (TYPE_OTHER, 'أخرى'),
    ]
    
    # Core fields
    title = models.CharField(max_length=255, verbose_name=_('العنوان'))
    slug = models.SlugField(max_length=300, unique=True, blank=True, verbose_name=_('رابط مخصص'))
    description = models.TextField(blank=True, null=True, verbose_name=_('الوصف'))
    file = models.FileField(
        upload_to=document_upload_path, 
        verbose_name=_('الملف'),
        help_text=_('الحد الأقصى لحجم الملف 50 ميجابايت')
    )
    
    # Metadata
    file_type = models.CharField(
        max_length=10, 
        blank=True, 
        verbose_name=_('نوع الملف')
    )
    file_size = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('حجم الملف'))
    page_count = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('عدد الصفحات'))
    
    # Status and visibility
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PUBLISHED,
        verbose_name=_('الحالة')
    )
    is_public = models.BooleanField(default=True, verbose_name=_('عام'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('آخر تحديث'))
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name=_('تاريخ الرفع'))
    last_viewed = models.DateTimeField(blank=True, null=True, verbose_name=_('آخر معاينة'))
    last_accessed = models.DateTimeField(blank=True, null=True, verbose_name=_('آخر وصول'))
    
    # Relationships
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
        verbose_name=_('تم الرفع بواسطة')
    )
    
    # Custom manager
    objects = DocumentManager()
    
    class Meta:
        verbose_name = _('مستند')
        verbose_name_plural = _('المستندات')
        ordering = ['-uploaded_at']
        permissions = [
            ('can_share_document', _('يمكنه مشاركة المستندات')),
            ('can_manage_document', _('يمكنه إدارة المستندات')),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Generate slug from title if not set
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Handle file processing
        if self.file:
            # Set file size
            self.file_size = self.file.size
            
            # Determine file type
            self.file_type = self.get_file_extension().lstrip('.').lower()
            
            # Process PDF files to extract metadata
            if self.is_pdf():
                self._process_pdf_metadata()
        
        # Set timestamps
        if not self.pk:
            self.uploaded_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def _process_pdf_metadata(self):
        """Extract metadata from PDF files"""
        try:
            # Use PyMuPDF to get PDF metadata
            with fitz.open(self.file.path) as doc:
                self.page_count = doc.page_count
        except Exception as e:
            # Log the error but don't fail the save
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing PDF metadata for {self.file.path}: {e}")
    
    def get_absolute_url(self):
        """Get the canonical URL for this document"""
        return reverse('pdf_reader:document_detail', kwargs={'pk': self.pk})
    
    def get_download_url(self):
        """Get the download URL for this document"""
        return reverse('pdf_reader:document_download', kwargs={'pk': self.pk})
    
    def get_viewer_url(self):
        """Get the URL for the document viewer"""
        return reverse('pdf_reader:document_view', kwargs={'pk': self.pk})
    
    def get_edit_url(self):
        """Get the edit URL for this document"""
        return reverse('pdf_reader:document_update', kwargs={'pk': self.pk})
    
    def get_delete_url(self):
        """Get the delete URL for this document"""
        return reverse('pdf_reader:document_delete', kwargs={'pk': self.pk})
    
    def get_file_extension(self):
        """Get the file extension in lowercase"""
        return os.path.splitext(self.file.name)[1].lower()
    
    def get_file_name(self):
        """Get the original filename without path"""
        return os.path.basename(self.file.name)
    
    def get_file_size_display(self):
        """Return human-readable file size"""
        if not self.file_size:
            return "0 B"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0 or unit == 'GB':
                break
            size /= 1024.0
        
        return f"{size:.1f} {unit}"
    
    def is_pdf(self):
        """Check if the document is a PDF"""
        return self.file_type == 'pdf' or self.get_file_extension() == '.pdf'
