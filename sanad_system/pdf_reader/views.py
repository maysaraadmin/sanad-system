import fitz  # PyMuPDF
import logging
import os
import sys
import json
import uuid
import re
import mimetypes
from datetime import datetime, timedelta
from django.http import JsonResponse, FileResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
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
        # Start with the base queryset and select_related to avoid N+1 queries
        queryset = Document.objects.select_related('uploaded_by')
        
        # Apply search filter with proper indexing
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(uploaded_by__username__icontains=search_query)
            )
        
        # Filter by document type using database indexes
        doc_type = self.request.GET.get('type')
        if doc_type == 'pdf':
            queryset = queryset.filter(file__iendswith='.pdf')
        elif doc_type == 'doc':
            queryset = queryset.filter(
                Q(file__iendswith='.doc') | Q(file__iendswith='.docx')
            )
        elif doc_type == 'image':
            queryset = queryset.filter(
                Q(file__iendswith='.jpg') | 
                Q(file__iendswith='.jpeg') | 
                Q(file__iendswith='.png') |
                Q(file__iendswith='.gif')
            )
        
        # For non-staff users, only show public documents or their own documents
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(is_public=True) | Q(uploaded_by=self.request.user)
            )
        
        # Only count once after all filters are applied
        self.total_count = queryset.count()
        
        # Order by most recent first with a secondary sort on ID for consistent pagination
        return queryset.order_by('-uploaded_at', '-id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('المكتبة')
        context['search_query'] = self.request.GET.get('q', '')
        context['doc_type'] = self.request.GET.get('type', '')
        
        # Add pagination information
        page_obj = context.get('page_obj')
        if page_obj:
            context['show_pagination'] = page_obj.has_other_pages()
            context['total_count'] = getattr(self, 'total_count', 0)
            
            # Calculate start and end indices for the current page
            start_index = (page_obj.number - 1) * self.paginate_by + 1
            end_index = min(page_obj.number * self.paginate_by, self.total_count)
            
            context['start_index'] = start_index
            context['end_index'] = end_index
        
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
        
    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        # Allow embedding in iframes from the same origin
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

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
    """Serve the document file for viewing with proper caching and security."""
    document = get_object_or_404(Document, pk=pk)
    
    # Check permissions
    if not document.is_public and document.uploaded_by != request.user and not request.user.is_staff:
        raise Http404("You don't have permission to view this document.")
    
    file_path = document.file.path
    file_name = os.path.basename(file_path)
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise Http404("The requested file does not exist.")
    
    # Get file size for Content-Length header
    file_size = os.path.getsize(file_path)
    
    # For PDFs, we can serve them directly in the browser with proper headers
    if file_name.lower().endswith('.pdf'):
        # Open the file in binary mode
        file = open(file_path, 'rb')
        
        # Create a FileResponse with streaming
        response = FileResponse(file, content_type='application/pdf')
        
        # Set content disposition to inline for PDFs (view in browser)
        response['Content-Disposition'] = f'inline; filename="{file_name}"'
        
        # Set cache headers (1 day cache)
        response['Cache-Control'] = 'public, max-age=86400'  # 24 hours
        response['Expires'] = (datetime.now() + timedelta(days=1)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Set content length
        response['Content-Length'] = file_size
        
        # Set last modified header
        response['Last-Modified'] = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Handle range requests for partial content (useful for large PDFs)
        range_header = request.META.get('HTTP_RANGE', '').strip()
        if range_header.startswith('bytes='):
            ranges = range_header[6:].split('-')
            range_start = int(ranges[0]) if ranges[0] else 0
            range_end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
            
            if range_end >= file_size:
                range_end = file_size - 1
                
            content_length = range_end - range_start + 1
            
            response.status_code = 206  # Partial Content
            response['Content-Range'] = f'bytes {range_start}-{range_end}/{file_size}'
            response['Content-Length'] = content_length
            
            # Seek to the requested range
            file.seek(range_start)
            response.file_to_stream = file
            
            # Use StreamingHttpResponse for large files
            from django.http import StreamingHttpResponse
            response = StreamingHttpResponse(
                file,
                status=206,
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'inline; filename="{file_name}"'
            response['Content-Range'] = f'bytes {range_start}-{range_end}/{file_size}'
            response['Content-Length'] = content_length
            
        return response
    
    # For other file types, force download with streaming for large files
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    response['Content-Length'] = file_size
    return response

@login_required
@require_http_methods(["POST"])
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
def pdf_viewer(request, pk, page=1):
    """
    View for rendering PDF files as images using PyMuPDF.
    
    Args:
        request: HTTP request object
        pk: Primary key of the document
        page: Page number to display (1-based index)
        
    Returns:
        Rendered template with PDF viewer or image data for AJAX requests
    """
    logger.info(f"PDF viewer requested for document {pk}, page {page}")
    
    document = None
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        document = get_object_or_404(Document, pk=pk)
        logger.info(f"Document found: {document.title} (ID: {document.id})")
        
        # Check if user has permission to view this document
        if not document.is_public and document.uploaded_by != request.user and not request.user.is_staff:
            logger.warning(f"Permission denied for user {request.user} to view document {pk}")
            raise Http404(_("You don't have permission to view this document."))
        
        # Get total pages from PDF
        total_pages = 1
        try:
            with fitz.open(document.file.path) as doc:
                total_pages = doc.page_count
        except Exception as e:
            logger.error(f"Error getting page count for document {pk}: {str(e)}")
        
        # Check if the file exists
        if not document.file:
            logger.error(f"Document {pk} has no file associated with it")
            raise Http404(_("The requested file could not be found."))
            
        # For AJAX requests, return the page image
        if is_ajax:
            file_path = document.file.path if hasattr(document.file, 'path') else None
            if not file_path or not os.path.exists(file_path):
                logger.error(f"File not found at path: {file_path}")
                if not document.file.url:
                    return JsonResponse({
                        'success': False,
                        'error': 'File not found',
                        'message': _('The requested file could not be found.')
                    }, status=404)
                # Try to serve via URL if available
                return JsonResponse({
                    'success': True,
                    'redirect_url': document.file.url
                })
        
        # For non-AJAX requests, check if the file is a PDF
        if not document.is_pdf():
            logger.warning(f"Non-PDF file requested for PDF viewer: {document.file.name}")
            if document.file.url:
                return redirect(document.file.url)
            raise Http404(_("The requested file is not a PDF and cannot be displayed in the viewer."))
        
        # Update last viewed timestamp
        document.last_viewed = timezone.now()
        document.save(update_fields=['last_viewed'])
        
        # Get the page number from URL or query parameters
        page_num = int(page) if str(page).isdigit() else 1
        if 'page' in request.GET and request.GET['page'].isdigit():
            page_num = int(request.GET['page'])
        
        logger.info(f"Processing request - Page: {page_num}, AJAX: {is_ajax}")
        
        # Initialize total_pages in case we can't open the document
        total_pages = 1
        
        with fitz.open(document.file.path) as doc:
            # Get total pages
            total_pages = doc.page_count
            logger.info(f"PDF opened successfully. Total pages: {total_pages}")
            
            # Validate page number
            page_num = max(1, min(page_num, total_pages))
            
            # Handle AJAX requests for page images
            if is_ajax:
                try:
                    logger.debug(f"Loading page {page_num}")
                    # Get the requested page
                    page = doc.load_page(page_num - 1)
                    
                    # Get zoom level from request
                    zoom = float(request.GET.get('zoom', 1.5))
                    logger.debug(f"Zoom level: {zoom}")
                    
                    # Create a matrix for zooming
                    mat = fitz.Matrix(zoom, zoom)
                    
                    # Render page to an image (pixmap)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    
                    # Convert to PNG
                    img_data = pix.tobytes('png')
                    
                    # Create response
                    response = HttpResponse(img_data, content_type='image/png')
                    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response['Pragma'] = 'no-cache'
                    response['Expires'] = '0'
                    response['X-Frame-Options'] = 'SAMEORIGIN'
                    response['Content-Security-Policy'] = "frame-ancestors 'self'"
                    
                    logger.debug(f"Successfully rendered page {page_num}")
                    return response
                    
                except Exception as e:
                    error_msg = f"Error rendering PDF page {page_num}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    return JsonResponse({
                        'success': False,
                        'error': str(e),
                        'message': _('Error rendering PDF page.')
                    }, status=500)
        
        # For regular requests, render the PDF viewer template
        context = {
            'document': document,
            'page': page,
            'total_pages': total_pages,
            'zoom_level': float(request.GET.get('zoom', 1.0)),
            'can_download': document.uploaded_by == request.user or request.user.is_staff,
            'can_edit': document.uploaded_by == request.user or request.user.is_staff,
        }
        
        response = render(request, 'pdf_reader/pdf_viewer.html', context)
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response
        
    except Http404 as e:
        # Re-raise 404 errors
        raise e
    except Exception as e:
        error_msg = f"Unexpected error in PDF viewer: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        if is_ajax:
            return JsonResponse({
                'success': False,
                'error': 'server_error',
                'message': _('An error occurred while processing your request. Please try again later.')
            }, status=500)
            
        # For non-AJAX requests, render the error page
        context = {
            'document': document if document else None,
            'page_title': _('Error - PDF Viewer'),
            'current_page': 1,
            'total_pages': 1,
            'can_download': False,
            'can_edit': False,
            'error_message': _("An unexpected error occurred. Please try again later.")
        }
        response = render(request, 'pdf_reader/pdf_viewer.html', context)
        
        # Add security headers
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Content-Security-Policy'] = "frame-ancestors 'self'"
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response

@login_required
def document_info(request, pk):
    """
    Get information about a document for the debug tool.
    Returns JSON with document metadata and permissions.
    """
    try:
        document = get_object_or_404(Document, pk=pk)
        
        # Check permissions
        can_view = (
            document.is_public or 
            document.uploaded_by == request.user or 
            request.user.is_staff
        )
        
        if not can_view:
            return JsonResponse({
                'error': 'Permission denied',
                'has_permission': False
            }, status=403)
        
        # Get file info
        file_info = {
            'name': os.path.basename(document.file.name),
            'size': document.file.size,
            'url': document.file.url if hasattr(document.file, 'url') else None,
            'exists': os.path.exists(document.file.path) if hasattr(document.file, 'path') else False
        }
        
        # Get PDF-specific info if available
        pdf_info = {}
        if hasattr(document, 'page_count'):
            pdf_info['page_count'] = document.page_count
        
        # Check if file is a PDF
        is_pdf = file_info['name'].lower().endswith('.pdf')
        pdf_info['is_pdf'] = is_pdf
        
        # Try to get page count if not already set
        if is_pdf and 'page_count' not in pdf_info and hasattr(document.file, 'path'):
            try:
                with fitz.open(document.file.path) as doc:
                    pdf_info['page_count'] = doc.page_count
                    # Update the document's page count if it's not set
                    if not hasattr(document, 'page_count') or document.page_count is None:
                        document.page_count = doc.page_count
                        document.save(update_fields=['page_count'])
            except Exception as e:
                logger.error(f"Error getting PDF page count: {str(e)}")
                pdf_info['error'] = str(e)
        
        # Build the download URL
        download_url = reverse('pdf_reader:document_download', kwargs={'pk': document.pk})
        
        response_data = {
            'success': True,
            'id': document.id,
            'title': document.title,
            'uploaded_by': document.uploaded_by.username,
            'uploaded_at': document.uploaded_at.isoformat(),
            'is_public': document.is_public,
            'file': file_info,
            'pdf': pdf_info,
            'has_permission': True,
            'can_download': True,
            'can_edit': document.uploaded_by == request.user or request.user.is_staff,
            'download_url': request.build_absolute_uri(download_url)
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.exception("Error in document_info view")
        return JsonResponse({
            'error': str(e),
            'has_permission': False
        }, status=500)

def pdf_metadata(request, pk):
    """
    Get metadata about a PDF document.
    """
    document = get_object_or_404(Document, pk=pk)
    
    # Check permissions
    if not document.is_public and document.uploaded_by != request.user and not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'error': _('Permission denied')
        }, status=403)
    
    try:
        with fitz.open(document.file.path) as doc:
            return JsonResponse({
                'success': True,
                'total_pages': doc.page_count,
                'title': document.title,
                'download_url': request.build_absolute_uri(document.get_download_url())
            })
    except Exception as e:
        logger.error(f"Error getting PDF metadata: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': _('Error getting PDF metadata')
        }, status=500)
    return render(request, template, context)

logger = logging.getLogger(__name__)

def pdf_reader_home(request):
    """Render the PDF reader upload form"""
    return render(request, 'pdf_reader/base_pdf_reader.html')

@require_http_methods(["POST"])
@login_required
def upload_pdf(request):
    """Handle PDF file uploads with security validation."""
    if request.method != 'POST':
        logger.warning("Request method not allowed: %s", request.method)
        return JsonResponse({
            'status': 'error',
            'message': 'Only POST method is allowed',
            'code': 'method_not_allowed'
        }, status=405)
    
    # Check if file was provided
    if 'pdf_file' not in request.FILES:
        logger.warning("No file in request")
        return JsonResponse({
            'status': 'error',
            'message': 'No file was provided in the request',
            'code': 'no_file_provided'
        }, status=400)
    
    pdf_file = request.FILES['pdf_file']
    
    # Validate file size (max 50MB)
    max_size = 50 * 1024 * 1024  # 50MB
    if pdf_file.size > max_size:
        return JsonResponse({
            'status': 'error',
            'message': 'File size exceeds the maximum limit of 50MB',
            'code': 'file_too_large',
            'max_size': max_size,
            'file_size': pdf_file.size
        }, status=400)
    
    # Validate file type using magic numbers
    import magic
    from django.core.files.uploadedfile import InMemoryUploadedFile
    
    # Read first 2048 bytes for file type detection
    file_content = b''
    if hasattr(pdf_file, 'temporary_file_path'):
        with open(pdf_file.temporary_file_path(), 'rb') as f:
            file_content = f.read(2048)
    else:
        if isinstance(pdf_file, InMemoryUploadedFile):
            file_content = pdf_file.read(2048)
            pdf_file.seek(0)  # Reset file pointer
    
    # Check if file is actually a PDF using magic numbers
    if file_content:
        file_mime = magic.from_buffer(file_content, mime=True)
        if file_mime != 'application/pdf':
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid file type. Only PDF files are allowed.',
                'code': 'invalid_file_type',
                'detected_type': file_mime
            }, status=400)
    
    # Additional filename validation
    import re
    if not re.match(r'^[\w\-. ]+\.pdf$', pdf_file.name, re.IGNORECASE):
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid filename. Only alphanumeric, spaces, hyphens, underscores, and dots are allowed.',
            'code': 'invalid_filename'
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
        file_path: Relative path to the PDF file in the documents directory
        
    Returns:
        FileResponse with the PDF file or error response
    """
    try:
        logger.info(f"PDF request received for file: {file_path}")
        
        # Security check: Basic validation
        if not file_path or not isinstance(file_path, str):
            logger.error("No file path provided")
            return HttpResponse("No file specified", status=400)
            
        # Normalize and clean the path
        file_path = file_path.strip()
        if not file_path:
            return HttpResponse("Invalid file path", status=400)
            
        # Check for path traversal attempts and other invalid characters
        if any([
            '..' in file_path,
            file_path.startswith('/'),
            '~' in file_path,
            '//' in file_path,
            '\\' in file_path,
            ':' in file_path.replace(':/', ''),  # Allow Windows drive letters
        ]):
            logger.error(f"Suspicious path detected: {file_path}")
            return HttpResponse("Invalid file path", status=400)
            
        # Construct full file path - look in the documents/ directory
        base_dir = os.path.abspath(os.path.join(settings.MEDIA_ROOT, 'documents'))
        full_path = os.path.abspath(os.path.join(base_dir, file_path))
        
        # Verify the resolved path is still within the base directory
        if not full_path.startswith(base_dir):
            logger.error(f"Security violation: Attempted directory traversal: {file_path}")
            return HttpResponse("Invalid file path", status=400)
            
        # Check if file exists and is a file
        if not os.path.isfile(full_path):
            logger.warning(f"PDF file not found: {full_path}")
            return HttpResponse("File not found", status=404)
            
        # Verify file extension
        _, ext = os.path.splitext(full_path)
        if ext.lower() != '.pdf':
            logger.warning(f"Invalid file type: {full_path}")
            return HttpResponse("Invalid file type", status=400)
            
        # Check file size (prevent serving extremely large files directly)
        file_size = os.path.getsize(full_path)
        max_size = getattr(settings, 'MAX_PDF_FILE_SIZE', 50 * 1024 * 1024)  # 50MB default
        if file_size > max_size:
            logger.warning(f"File too large: {full_path} ({file_size} bytes)")
            return HttpResponse("File too large", status=413)
            
        # Set content type and disposition
        content_type = 'application/pdf'
        filename = os.path.basename(full_path)
        
        # Use FileResponse with context manager to ensure file handle is closed
        response = FileResponse(
            open(full_path, 'rb'),
            content_type=content_type,
            as_attachment=False,  # Display in browser
            filename=filename
        )
        
        # Security headers
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(filename)}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'same-origin'
        
        # Enable CORS if needed (be specific with allowed origins in production)
        response['Access-Control-Allow-Origin'] = getattr(settings, 'CORS_ALLOWED_ORIGINS', '*')
        
        # Cache control (adjust as needed)
        response['Cache-Control'] = 'private, max-age=86400'  # 24 hours
        
        logger.info(f"Successfully served PDF: {filename} ({file_size} bytes)")
        return response
        
    except (ValueError, TypeError) as ve:
        logger.error(f"Validation error serving PDF: {str(ve)}", exc_info=True)
        return HttpResponse("Invalid request", status=400)
    except PermissionError:
        logger.error(f"Permission denied accessing file: {file_path}", exc_info=True)
        return HttpResponse("Access denied", status=403)
    except FileNotFoundError:
        logger.warning(f"File not found: {file_path}")
        return HttpResponse("File not found", status=404)
    except OSError as oe:
        logger.error(f"OS error serving file {file_path}: {str(oe)}", exc_info=True)
        return HttpResponse("Error accessing file", status=500)
    except Exception as e:
        logger.error(f"Unexpected error serving PDF: {str(e)}", exc_info=True)
        return HttpResponse("An error occurred", status=500)

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
