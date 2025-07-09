import os
import mimetypes
import fitz  # PyMuPDF
from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _
import uuid
import re

def document_upload_path(instance, filename):
    """
    Generate a unique file path for the uploaded document.
    
    Args:
        instance: The Document instance being saved
        filename: The original filename
        
    Returns:
        str: A safe file path for the uploaded document
    """
    # Get the file extension
    ext = os.path.splitext(filename)[1].lower()
    
    # Create a safe base filename
    if hasattr(instance, 'title') and instance.title:
        base_name = slugify(instance.title)
        if not base_name:  # In case slugify returns empty string
            base_name = 'document'
    else:
        base_name = 'document'
    
    # Add timestamp and random string for uniqueness
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random_str = uuid.uuid4().hex[:8]  # Add random string for extra uniqueness
    safe_filename = f"{base_name}_{timestamp}_{random_str}{ext}"
    
    # Ensure the filename is safe
    safe_filename = re.sub(r'[^\w\-_.]', '_', safe_filename)
    
    # Create year/month subdirectories for better organization
    date_path = timezone.now().strftime('%Y/%m')
    
    return os.path.join('documents', date_path, safe_filename)

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
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        
        is_new = self.pk is None
        file_changed = False
        
        # Check if file has changed
        if self.file:
            try:
                old_instance = Document.objects.get(pk=self.pk) if not is_new else None
                if is_new or (old_instance and old_instance.file != self.file):
                    file_changed = True
            except Document.DoesNotExist:
                file_changed = True
        
        # Handle file processing
        if file_changed or is_new:
            # Set file size
            self.file_size = self.file.size if self.file else 0
            
            # Determine file type from filename
            if self.file:
                self.file_type = self.get_file_extension().lstrip('.').lower()
        
        # Set timestamps
        if is_new:
            self.uploaded_at = timezone.now()
        
        # Save the model first
        super().save(*args, **kwargs)
        
        # Process PDF in background if it's a new or changed PDF file
        if file_changed and self.is_pdf():
            self._process_pdf_async()
    
    def _process_pdf_async(self):
        """Trigger background task to process PDF metadata"""
        from .tasks import process_pdf_metadata
        
        try:
            # Start the background task
            process_pdf_metadata.delay(self.pk)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error scheduling PDF processing task for document {self.pk}: {e}")
    
    def extract_text_async(self):
        """Start background task to extract text from PDF"""
        from .tasks import extract_text_from_pdf_task
        
        if not self.is_pdf():
            return None
            
        try:
            return extract_text_from_pdf_task.delay(self.pk)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error scheduling text extraction task for document {self.pk}: {e}")
            return None
    
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
        # Check both the stored file_type and the actual file extension
        if not hasattr(self, 'file') or not self.file:
            return False
            
        # Check file extension first (faster)
        ext = self.get_file_extension()
        if ext == '.pdf':
            return True
            
        # If no extension or not .pdf, check the file signature
        try:
            if hasattr(self.file, 'path') and os.path.exists(self.file.path):
                with open(self.file.path, 'rb') as f:
                    header = f.read(4)
                    # PDF file signature
                    return header == b'%PDF'
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error checking if file is PDF: {e}")
            
        return False
