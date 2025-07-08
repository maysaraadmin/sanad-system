import fitz  # PyMuPDF
import logging
import os
import sys
import json
import uuid
import re
import mimetypes
from datetime import datetime
from django.http import JsonResponse, FileResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.conf import settings
from django.utils.translation import gettext as _
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Document
from .forms import DocumentForm

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'pdf_reader/document_list.html'
    context_object_name = 'documents'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Document.objects.all()
        
        # Apply search filter
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(uploaded_by__username__icontains=search_query)
            )
        
        # Filter by document type
        doc_type = self.request.GET.get('type')
        if doc_type == 'pdf':
            queryset = queryset.filter(file__iendswith='.pdf')
        elif doc_type == 'doc':
            queryset = queryset.filter(
                Q(file__iendswith='.doc') | Q(file__iendswith='.docx')
            )
        
        # For non-staff users, only show public documents or their own documents
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(is_public=True) | Q(uploaded_by=self.request.user)
            )
        
        # Order by most recent first
        return queryset.order_by('-uploaded_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('المكتبة')
        context['search_query'] = self.request.GET.get('q', '')
        context['doc_type'] = self.request.GET.get('type', '')
        return context

class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = Document
    template_name = 'pdf_reader/document_detail.html'
    context_object_name = 'document'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # For non-staff users, only allow access to public documents or their own documents
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(is_public=True) | Q(uploaded_by=self.request.user)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.get_object()
        
        # Get related documents (same uploader, same type, excluding current document)
        related_documents = Document.objects.filter(
            uploaded_by=document.uploaded_by,
            file__endswith=os.path.splitext(document.file.name)[1]
        ).exclude(pk=document.pk)[:5]
        
        context.update({
            'page_title': document.title,
            'related_documents': related_documents,
            'is_owner': self.request.user == document.uploaded_by or self.request.user.is_staff,
            'can_edit': self.request.user == document.uploaded_by or self.request.user.is_staff,
            'can_delete': self.request.user == document.uploaded_by or self.request.user.is_staff,
        })
        
        return context

class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'pdf_reader/document_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, _('تم رفع المستند بنجاح.'))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('رفع مستند جديد'),
            'submit_button': _('رفع المستند'),
            'cancel_url': reverse_lazy('pdf_reader:document_list'),
        })
        return context
    
    def get_success_url(self):
        return reverse_lazy('pdf_reader:document_detail', kwargs={'pk': self.object.pk})

class DocumentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = 'pdf_reader/document_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, _('تم تحديث المستند بنجاح.'))
        return super().form_valid(form)
    
    def test_func(self):
        document = self.get_object()
        return self.request.user == document.uploaded_by or self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('تعديل المستند: {}').format(self.object.title),
            'submit_button': _('حفظ التغييرات'),
            'cancel_url': reverse_lazy('pdf_reader:document_detail', kwargs={'pk': self.object.pk}),
        })
        return context
    
    def get_success_url(self):
        return reverse_lazy('pdf_reader:document_detail', kwargs={'pk': self.object.pk})

class DocumentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Document
    template_name = 'pdf_reader/document_confirm_delete.html'
    success_url = reverse_lazy('pdf_reader:document_list')
    
    def test_func(self):
        document = self.get_object()
        return self.request.user == document.uploaded_by or self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('تأكيد حذف المستند'),
            'cancel_url': reverse_lazy('pdf_reader:document_detail', kwargs={'pk': self.object.pk}),
        })
        return context
    
    def delete(self, request, *args, **kwargs):
        document = self.get_object()
        document.delete()
        messages.success(request, _('تم حذف المستند بنجاح.'))
        return redirect(self.get_success_url())

def serve_document(request, pk):
    """Serve the document file for viewing"""
    document = get_object_or_404(Document, pk=pk)
    
    # Check permissions
    if not document.is_public and document.uploaded_by != request.user and not request.user.is_staff:
        raise Http404("You don't have permission to view this document.")
    
    file_path = document.file.path
    file_name = os.path.basename(file_path)
    
    # For PDFs, we can serve them directly in the browser
    if file_name.lower().endswith('.pdf'):
        return FileResponse(open(file_path, 'rb'), content_type='application/pdf')
    
    # For other file types, force download
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    return response

@login_required
def toggle_public_status(request, pk):
    """
    Toggle the public status of a document.
    
    Args:
        request: HTTP request object
        pk: Primary key of the document
        
    Returns:
        JsonResponse with the new status
    """
    if request.method == 'POST':
        document = get_object_or_404(Document, pk=pk, owner=request.user)
        document.is_public = not document.is_public
        document.save()
        return JsonResponse({
            'status': 'success',
            'is_public': document.is_public,
            'message': 'Document visibility updated successfully.'
        })
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@login_required
def pdf_viewer(request, pk, page=None):
    """
    View for PDF.js viewer with support for direct page navigation.
    
    Args:
        request: HTTP request object
        pk: Primary key of the document
        page: Optional page number to navigate to (1-based index)
        
    Returns:
        Rendered template with PDF viewer
    """
    document = get_object_or_404(Document, pk=pk)
    
    # Check if user has permission to view this document
    if not document.is_public and document.uploaded_by != request.user and not request.user.is_staff:
        raise Http404(_("You don't have permission to view this document."))
    
    # Check if the file exists
    if not document.file:
        raise Http404(_("The requested file does not exist."))
    
    # Get the absolute file path and check if it exists
    if not os.path.exists(document.file.path):
        raise Http404(_("The requested file could not be found on the server."))
    
    # Check if the file is a PDF
    if not document.is_pdf():
        # For non-PDF files, redirect to download
        return redirect(document.file.url)
    
    # Update last viewed timestamp
    document.last_viewed = timezone.now()
    document.save(update_fields=['last_viewed'])
    
    # Get the URL for the PDF file (use the direct URL for better performance)
    pdf_url = request.build_absolute_uri(document.file.url)
    
    # If this is an AJAX request, return JSON data for the PDF viewer component
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Get PDF metadata using PyMuPDF
            with fitz.open(document.file.path) as doc:
                total_pages = doc.page_count
                
                # Validate page number
                page_num = int(page) if page and str(page).isdigit() else 1
                page_num = max(1, min(page_num, total_pages))
                
                # Get page dimensions
                page = doc.load_page(page_num - 1)
                rect = page.rect
                
                return JsonResponse({
                    'success': True,
                    'document': {
                        'title': document.title,
                        'total_pages': total_pages,
                        'current_page': page_num,
                        'page_width': rect.width,
                        'page_height': rect.height,
                        'url': pdf_url,
                        'download_url': request.build_absolute_uri(document.get_download_url())
                    }
                })
                
        except Exception as e:
            logger.error(f"Error getting PDF metadata: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': str(e),
                'message': _('Error loading PDF document.')
            }, status=500)
    
    # For regular requests, render the full page with the PDF viewer
    context = {
        'document': document,
        'pdf_url': pdf_url,
        'page_title': f"{document.title} - {_('PDF Viewer')}",
        'current_page': int(page) if page and str(page).isdigit() else 1,
        'is_embed': request.GET.get('embed', '').lower() in ('true', '1', 'yes'),
        'can_download': document.uploaded_by == request.user or request.user.is_staff,
        'can_edit': document.uploaded_by == request.user or request.user.is_staff,
    }
    
    # If this is an embedded view, use a simpler template
    template = 'pdf_reader/pdf_viewer_embed.html' if context['is_embed'] else 'pdf_reader/pdf_viewer.html'
    
    return render(request, template, context)

logger = logging.getLogger(__name__)

def pdf_reader_home(request):
    """Render the PDF reader upload form"""
    return render(request, 'pdf_reader/base_pdf_reader.html')

def upload_pdf(request):
    """Handle PDF file uploads with security validation."""
    if request.method != 'POST':
        logger.warning("Request method not allowed: %s", request.method)
        return JsonResponse({
            'status': 'error',
            'message': 'Only POST method is allowed'
        }, status=405)
    
    # Check if file was provided
    if 'pdf_file' not in request.FILES:
        logger.warning("No file in request")
        return JsonResponse({
            'status': 'error',
            'message': 'No file was provided in the request'
        }, status=400)
    
    pdf_file = request.FILES['pdf_file']
    
    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    if pdf_file.size > max_size:
        return JsonResponse({
            'status': 'error',
            'message': 'File size exceeds the maximum limit of 10MB'
        }, status=400)
    
    # Validate file type
    if not pdf_file.name.lower().endswith('.pdf'):
        return JsonResponse({
            'status': 'error',
            'message': 'Only PDF files are allowed'
        }, status=400)
    
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'pdf_uploads')
        os.makedirs(upload_dir, exist_ok=True, mode=0o755)
        
        # Generate a unique filename to prevent directory traversal and overwrites
        import uuid
        import re
        
        # Sanitize the original filename
        original_name = re.sub(r'[^\w\-_. ]', '_', pdf_file.name)
        safe_filename = f"{uuid.uuid4().hex}_{original_name}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        # Ensure the file path is within the intended directory (security check)
        if not os.path.abspath(file_path).startswith(os.path.abspath(upload_dir)):
            raise ValueError("Invalid file path")
        
        # Save file
        with open(file_path, 'wb+') as destination:
            for chunk in pdf_file.chunks():
                destination.write(chunk)
        
        logger.info("File saved to: %s", file_path)
        
        # Extract text from PDF
        text = extract_text_from_pdf(file_path)
        
        if not text.strip():
            logger.warning("No text extracted from PDF")
            return JsonResponse({
                'status': 'warning',
                'message': 'The PDF was uploaded but no text could be extracted. It might be a scanned document or image-based PDF.',
                'filename': safe_filename,
                'text': '',
                'pages': 0,
                'uploaded_at': datetime.now().isoformat()
            })
        
        response_data = {
            'status': 'success',
            'filename': safe_filename,
            'text': text,
            'pages': len(text.split('\f')) if text else 0,
            'uploaded_at': datetime.now().isoformat()
        }
        
        logger.info("Successfully processed PDF. Pages: %d, Text length: %d", 
                   response_data['pages'], len(text))
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.exception("Error processing PDF upload")
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to process PDF: {str(e)}'
        }, status=500)

def extract_text_from_pdf(pdf_path, max_pages=1000):
    """
    Extract text from a PDF file with security and performance considerations.
    
    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to process (prevents DoS with large files)
        
    Returns:
        str: Extracted text with page separators
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        ValueError: If the PDF is invalid or encrypted with password
        RuntimeError: If there's an error processing the PDF
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Additional security check - verify it's a file and not a directory
    if not os.path.isfile(pdf_path):
        raise ValueError(f"Path is not a file: {pdf_path}")
    
    doc = None
    try:
        # Open the PDF file in read-only mode
        doc = fitz.open(pdf_path)
        
        # Check if the document is encrypted
        if doc.is_encrypted:
            logger.warning("PDF is encrypted, attempting to open with empty password")
            if not doc.authenticate(""):
                raise ValueError("PDF is encrypted and cannot be opened with empty password")
        
        # Limit the number of pages to process
        total_pages = len(doc)
        if total_pages > max_pages:
            logger.warning("PDF has %d pages, limiting to first %d pages", total_pages, max_pages)
            total_pages = max_pages
        
        text_parts = []
        processed_pages = 0
        
        # Process each page
        for page_num in range(total_pages):
            try:
                page = doc.load_page(page_num)
                page_text = page.get_text("text")
                
                if page_text and page_text.strip():
                    text_parts.append(page_text)
                    processed_pages += 1
                else:
                    logger.debug("No text found on page %d", page_num + 1)
                
                # Periodically check if we're using too much memory
                if processed_pages % 10 == 0 and sys.getsizeof(text_parts) > 10 * 1024 * 1024:  # 10MB
                    logger.warning("Large PDF detected (%d MB), truncating extraction", 
                                 sys.getsizeof(text_parts) // (1024 * 1024))
                    break
                    
            except Exception as page_error:
                logger.error("Error extracting text from page %d: %s", 
                           page_num + 1, str(page_error), exc_info=True)
                continue
        
        # Join all page texts with form feed as page separator
        return "\f".join(text_parts).strip()
        
    except fitz.FileDataError as fde:
        logger.error("Invalid PDF file: %s", str(fde), exc_info=True)
        raise ValueError("Invalid or corrupted PDF file") from fde
        
    except Exception as e:
        logger.error("Error extracting text from PDF: %s", str(e), exc_info=True)
        raise RuntimeError(f"Failed to extract text from PDF: {str(e)}") from e
        
    finally:
        # Ensure the document is always properly closed
        if doc is not None:
            try:
                doc.close()
            except Exception as e:
                logger.error("Error closing PDF document: %s", str(e), exc_info=True)

def serve_pdf(request, file_path):
    """
    Serve PDF files with proper security checks.
    
    Args:
        request: HTTP request object
        file_path: Relative path to the PDF file in the media directory
        
    Returns:
        FileResponse with the PDF file or error response
    """
    try:
        logger.info(f"PDF request received for file: {file_path}")
        
        # Security check: Ensure the file path is safe
        if not file_path or any(c in file_path for c in ['..', '/', '\\']):
            logger.error(f"Invalid file path: {file_path}")
            return HttpResponse("Invalid file path", status=400)
            
        # Construct full file path - look in the documents/ directory
        base_dir = os.path.join(settings.MEDIA_ROOT, 'documents')
        full_path = os.path.normpath(os.path.join(base_dir, file_path))
        
        logger.info(f"Looking for PDF at: {full_path}")
        logger.info(f"Base directory: {base_dir}")
        logger.info(f"Media root: {settings.MEDIA_ROOT}")
        
        # Verify the file is within the intended directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
            logger.error(f"Security violation: Attempted to access file outside media directory: {full_path}")
            return HttpResponse("Invalid file path", status=400)
            
        # Check if file exists and is a file
        if not os.path.isfile(full_path):
            logger.warning(f"PDF file not found: {full_path}")
            # Check if the directory exists
            if not os.path.exists(os.path.dirname(full_path)):
                logger.warning(f"Directory does not exist: {os.path.dirname(full_path)}")
            return HttpResponse("PDF file not found", status=404)
            
        # Check file extension
        if not full_path.lower().endswith('.pdf'):
            logger.warning(f"Invalid file type: {full_path}")
            return HttpResponse("Invalid file type", status=400)
            
        # Open the file in binary mode and serve it
        logger.info(f"Serving PDF file: {full_path}")
        response = FileResponse(open(full_path, 'rb'), content_type='application/pdf')
        
        # Set content disposition to inline to display in browser
        filename = os.path.basename(full_path)
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        # Enable CORS if needed
        response['Access-Control-Allow-Origin'] = '*'
        
        logger.info(f"Successfully served PDF: {filename}")
        return response
        
    except ValueError as ve:
        logger.error(f"Security error serving PDF: {str(ve)}", exc_info=True)
        return HttpResponse("Invalid request", status=400)
    except Exception as e:
        logger.error(f"Error serving PDF: {str(e)}", exc_info=True)
        return HttpResponse(f"Error serving PDF: {str(e)}", status=500)

def get_pdf_metadata(request):
    """
    Get metadata of a PDF file with security validation.
    
    Args:
        request: HTTP GET request with 'file' parameter
        
    Returns:
        JsonResponse with metadata or error message
    """
    if request.method != 'GET':
        logger.warning("Invalid request method: %s", request.method)
        return JsonResponse({
            'status': 'error',
            'message': 'Only GET method is allowed'
        }, status=405)
    
    if 'file' not in request.GET:
        logger.warning("No file parameter in request")
        return JsonResponse({
            'status': 'error',
            'message': 'No file specified'
        }, status=400)
    
    try:
        # Validate filename to prevent directory traversal
        filename = request.GET['file']
        if not filename or any(c in filename for c in ['..', '/', '\\']):
            raise ValueError("Invalid filename")
            
        # Construct safe path
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'pdf_uploads')
        file_path = os.path.normpath(os.path.join(upload_dir, filename))
        
        # Verify the file is within the intended directory
        if not file_path.startswith(os.path.abspath(upload_dir)):
            raise ValueError("Invalid file path")
            
        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning("File not found: %s", file_path)
            return JsonResponse({
                'status': 'error',
                'message': 'File not found'
            }, status=404)
            
        # Open and read PDF metadata
        doc = None
        try:
            doc = fitz.open(file_path)
            metadata = doc.metadata.copy()  # Create a copy of the metadata
            metadata['pages'] = len(doc)
            
            # Remove any potentially sensitive information
            for field in ['producer', 'creator', 'modDate', 'creationDate']:
                if field in metadata:
                    metadata[field] = str(metadata[field])
            
            return JsonResponse({
                'status': 'success',
                'metadata': metadata
            })
            
        except Exception as e:
            logger.error("Error reading PDF metadata: %s", str(e), exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to read PDF metadata'
            }, status=500)
            
        finally:
            if doc:
                doc.close()
                
    except ValueError as ve:
        logger.warning("Invalid file parameter: %s", str(ve))
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid file parameter'
        }, status=400)
        
    except Exception as e:
        logger.error("Unexpected error in get_pdf_metadata: %s", str(e), exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred'
        }, status=500)
