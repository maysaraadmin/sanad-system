import os
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, DeleteView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, Http404, FileResponse
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.db.models import Q
import os
from django.conf import settings

from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse
import json

from .models import Document, DocumentCategory
from .forms import DocumentForm, DocumentSearchForm
from .utils import render_pdf_page_to_image
from .hadith_processor import process_document

class DocumentListView(ListView):
    model = Document
    template_name = 'library/document_list.html'
    context_object_name = 'documents'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Document.objects.filter(is_public=True)
        if self.request.user.is_authenticated:
            # Show both public and user's private documents
            queryset = Document.objects.filter(
                models.Q(is_public=True) | 
                models.Q(uploaded_by=self.request.user)
            )
        return queryset.select_related('category', 'uploaded_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = DocumentCategory.objects.all()
        return context

class DocumentCategoryView(DocumentListView):
    def get_queryset(self):
        category_id = self.kwargs.get('category_id')
        self.category = get_object_or_404(DocumentCategory, id=category_id)
        queryset = super().get_queryset()
        return queryset.filter(category=self.category)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_category'] = self.category
        return context

class DocumentDetailView(DetailView):
    model = Document
    template_name = 'library/document_detail.html'
    context_object_name = 'document'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            return queryset.filter(is_public=True)
        return queryset.filter(
            models.Q(is_public=True) | 
            models.Q(uploaded_by=self.request.user)
        )
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.get_object()
        context['file_url'] = document.file.url if document.file else None
        context['is_pdf'] = document.file_type == 'pdf'
        return context


class PDFPageView(View):
    """View to serve rendered PDF pages as images"""
    def get(self, request, pk, page=0):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            document = get_object_or_404(Document, pk=pk)
            
            # Check permissions
            if not document.is_public and document.uploaded_by != request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'You do not have permission to view this document'
                }, status=403)
            
            # Validate page number
            try:
                page = int(page)
                zoom = float(request.GET.get('zoom', 1.0))
            except (ValueError, TypeError) as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid page number or zoom level: {str(e)}'
                }, status=400)
            
            # Get the absolute path to the PDF file
            if not document.file:
                return JsonResponse({
                    'success': False,
                    'error': 'No file associated with this document'
                }, status=400)
                
            pdf_path = os.path.join(settings.MEDIA_ROOT, document.file.name)
            
            # Verify file exists
            if not os.path.exists(pdf_path):
                error_msg = f'PDF file not found at: {pdf_path}'
                logger.error(error_msg)
                return JsonResponse({
                    'success': False,
                    'error': 'The PDF file could not be found on the server.'
                }, status=404)
            
            # Render the PDF page
            try:
                result = render_pdf_page_to_image(
                    pdf_path, 
                    page_number=page,
                    zoom=zoom
                )
                
                return JsonResponse({
                    'success': True,
                    'image': result['image'],
                    'current_page': result['current_page'],  # 1-based
                    'total_pages': result['total_pages']
                })
                
            except Exception as e:
                error_msg = f'Error rendering PDF page: {str(e)}'
                logger.error(error_msg, exc_info=True)
                return JsonResponse({
                    'success': False,
                    'error': 'Could not render the PDF page. The file might be corrupted or in an unsupported format.'
                }, status=500)
                
        except Exception as e:
            error_msg = f'Unexpected error in PDFPageView: {str(e)}'
            logger.error(error_msg, exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred while processing your request.'
            }, status=500)

class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'library/document_form.html'
    success_url = reverse_lazy('library:document_list')
    
    def form_valid(self, form):
        try:
            form.instance.uploaded_by = self.request.user
            response = super().form_valid(form)
            messages.success(
                self.request, 
                _('تم رفع الملف "%s" بنجاح') % form.instance.title
            )
            return response
        except Exception as e:
            messages.error(
                self.request,
                _('حدث خطأ أثناء رفع الملف: %s') % str(e)
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        for field, errors in form.errors.items():
            field_label = form.fields[field].label if field in form.fields else field
            for error in errors:
                if field == '__all__':
                    messages.error(self.request, error)
                else:
                    messages.error(
                        self.request,
                        f"{field_label}: {error}" if field_label else error
                    )
        return super().form_invalid(form)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = Document
    template_name = 'library/document_confirm_delete.html'
    success_url = reverse_lazy('library:document_list')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(uploaded_by=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('تم حذف الملف بنجاح'))
        return response

@login_required
def document_download(request, pk):
    document = get_object_or_404(Document, pk=pk)
    
    # Check if the document is public or the user has permission
    if not document.is_public and document.uploaded_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden(_('You do not have permission to download this document'))
    
    # Get the file path and open the file
    file_path = document.file.path
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/octet-stream")
            response['Content-Disposition'] = f'attachment; filename={os.path.basename(file_path)}'
            return response
    raise Http404("File not found")


@login_required
@require_http_methods(["POST"])
def extract_hadiths(request, pk):
    """Extract hadiths and narrators from a document with progress tracking."""
    import logging
    import time
    import json
    from django.conf import settings
    from django.core.cache import cache
    from django.views.decorators.csrf import csrf_exempt
    from django.utils.translation import gettext_lazy as _
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    from django.http import JsonResponse
    from .models import Document
    
    logger = logging.getLogger(__name__)
    start_time = time.time()
    
    # Generate a unique task ID for this extraction
    task_id = f"extract_task_{pk}_{int(time.time())}"
    
    # Initialize progress in cache
    progress_data = {
        'status': 'pending',
        'progress': 0,
        'message': 'Starting extraction...',
        'document_id': pk,
        'start_time': time.time(),
        'total_hadiths': 0,
        'current_page': 0,
        'total_pages': 0
    }
    cache.set(task_id, progress_data, timeout=3600)  # Store for 1 hour
    
    def update_progress(progress, message, **kwargs):
        """Helper function to update progress in cache."""
        nonlocal progress_data
        current_page = kwargs.get('current_page', progress_data.get('current_page', 0))
        total_pages = kwargs.get('total_pages', progress_data.get('total_pages', 0))
        
        progress_data.update({
            'status': 'processing',
            'progress': min(int(progress), 95),  # Cap at 95% until complete
            'message': str(message),
            'current_page': current_page,
            'total_pages': total_pages,
            'last_updated': time.time()
        })
        
        if 'total_hadiths' in kwargs:
            progress_data['total_hadiths'] = int(kwargs['total_hadiths'])
            
        cache.set(task_id, progress_data, timeout=3600)
        logger.info(f"Progress: {progress}% - {message}")
    
    try:
        logger.info(f"Extracting hadiths from document {pk}")
        document = get_object_or_404(Document, pk=pk)
        
        # Log document info
        doc_info = {
            'title': document.title,
            'type': document.file_type,
            'size': f"{document.file.size/1024/1024:.2f}MB" if hasattr(document.file, 'size') else 'unknown',
            'uploaded_by': document.uploaded_by.username if document.uploaded_by else 'unknown'
        }
        logger.info(f"Document details: {doc_info}")
        
        # Update progress
        update_progress(5, "Analyzing document...", document_info=doc_info)
        
        # Check file size with a higher limit (100MB)
        max_file_size = getattr(settings, 'MAX_SYNC_FILE_SIZE', 100 * 1024 * 1024)  # 100MB default
        if hasattr(document.file, 'size') and document.file.size > max_file_size:
            error_msg = f'File too large: {document.file.size/1024/1024:.2f}MB. Maximum allowed size is 100MB.'
            logger.warning(error_msg)
            update_progress(100, error_msg, status='failed', error=error_msg)
            return JsonResponse({
                'success': False, 
                'error': _(error_msg),
                'task_id': task_id
            }, status=413)
        
        # For large files, process in chunks
        chunk_size = 10  # Process 10 pages at a time
        if document.file_type == 'pdf' and hasattr(document.file, 'size') and document.file.size > 20 * 1024 * 1024:  # > 20MB
            chunk_size = 5  # Smaller chunks for very large files
        
        # Check permissions
        if not document.is_public and document.uploaded_by != request.user and not request.user.is_staff:
            error_msg = 'You do not have permission to extract hadiths from this document'
            logger.warning(f"Permission denied for user {request.user} on document {pk}")
            update_progress(100, error_msg, status='failed', error=error_msg)
            return JsonResponse({
                'success': False, 
                'error': _(error_msg),
                'task_id': task_id
            }, status=403)
        
        # Import the processor here to avoid circular imports
        from .hadith_processor import process_document
        
        # Process the document to extract hadiths and narrators
        logger.info(f"Starting document processing for {document.title}")
        update_progress(10, "Starting extraction process...")
        
        try:
            # Call process_document with progress callback
            result = process_document(
                document, 
                progress_callback=update_progress,
                chunk_size=chunk_size
            )
        except Exception as e:
            logger.error(f"Error in process_document: {str(e)}", exc_info=True)
            raise Exception(_("Error processing document: {}").format(str(e)))
        
        logger.info(f"Document processing completed. Success: {result.get('success', False)}")
        
        if result.get('success'):
            # Update progress to completed
            total_hadiths = len(result.get('hadiths', []))
            hadiths_preview = result.get('hadiths', [])[:10]  # Store first 10 hadiths in cache
            
            progress_data.update({
                'status': 'completed',
                'progress': 100,
                'message': f"Successfully extracted {total_hadiths} hadiths",
                'total_hadiths': total_hadiths,
                'hadiths': hadiths_preview,
                'end_time': time.time(),
                'duration': time.time() - start_time,
                'completed': True
            })
            cache.set(task_id, progress_data, timeout=300)  # Store result for 5 minutes
            
            # Prepare the response data
            response_data = {
                'success': True,
                'task_id': task_id,
                'status': 'completed',
                'total_hadiths': total_hadiths,
                'hadiths': hadiths_preview
            }
            
            return JsonResponse(response_data)
        else:
            error_msg = result.get('error', _('Unknown error during extraction'))
            raise Exception(error_msg)
            
    except Exception as e:
        # Log the error
        error_msg = str(e)
        logger.error(f"Error extracting hadiths: {error_msg}", exc_info=True)
        
        # Update progress to failed
        progress_data.update({
            'status': 'failed',
            'progress': 100,
            'message': f"Error: {error_msg}",
            'error': error_msg,
            'end_time': time.time(),
            'duration': time.time() - start_time if 'start_time' in locals() else 0,
            'failed': True
        })
        cache.set(task_id, progress_data, timeout=300)
        
        return JsonResponse({
            'success': False,
            'task_id': task_id,
            'error': error_msg
        }, status=500)


class DocumentSearchView(LoginRequiredMixin, TemplateView):
    """View for searching documents in the library."""
    template_name = 'library/document_search.html'
    paginate_by = 10
    login_url = 'login'
    
    def get_queryset(self):
        """Get the base queryset for the search."""
        queryset = Document.objects.all()
        
        # Filter by public documents or user's private documents
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        elif not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(is_public=True) | Q(uploaded_by=self.request.user)
            )
            
        return queryset.select_related('category', 'uploaded_by')
    
    def get_context_data(self, **kwargs):
        """Add search form and results to the context."""
        context = super().get_context_data(**kwargs)
        
        # Initialize the form with GET data
        form = DocumentSearchForm(self.request.GET or None)
        context['form'] = form
        
        # Get the base queryset
        queryset = self.get_queryset()
        
        # Apply search filters if form is valid
        if form.is_valid():
            query = form.cleaned_data.get('query')
            category = form.cleaned_data.get('category')
            file_type = form.cleaned_data.get('file_type')
            
            # Apply search query
            if query:
                queryset = queryset.filter(
                    Q(title__icontains=query) |
                    Q(description__icontains=query) |
                    Q(file__icontains=query)
                )
            
            # Apply category filter
            if category:
                queryset = queryset.filter(category=category)
            
            # Apply file type filter
            if file_type:
                queryset = queryset.filter(file_type=file_type)
        
        # Add pagination
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        
        page = self.request.GET.get('page')
        paginator = Paginator(queryset, self.paginate_by)
        
        try:
            documents = paginator.page(page)
        except PageNotAnInteger:
            documents = paginator.page(1)
        except EmptyPage:
            documents = paginator.page(paginator.num_pages)
        
        context['documents'] = documents
        context['categories'] = DocumentCategory.objects.all()
        context['total_results'] = queryset.count()
        
        return context


@login_required
def check_extraction_progress(request, task_id):
    """Check the progress of an extraction task."""
    progress_data = cache.get(task_id)
    if not progress_data:
        return JsonResponse({
            'success': False,
            'error': 'Task not found or expired'
        }, status=404)
    
    # Remove sensitive data before sending to client
    response_data = {
        'task_id': task_id,
        'status': progress_data.get('status', 'unknown'),
        'progress': progress_data.get('progress', 0),
        'message': progress_data.get('message', ''),
        'current_page': progress_data.get('current_page', 0),
        'total_pages': progress_data.get('total_pages', 0),
        'total_hadiths': progress_data.get('total_hadiths', 0)
    }
    
    # If the task is completed or failed, include the result/error
    if progress_data['status'] in ['completed', 'failed']:
        response_data.update({
            'success': progress_data['status'] == 'completed',
            'error': progress_data.get('error'),
            'hadiths': progress_data.get('hadiths', []),
            'duration': progress_data.get('duration', 0)
        })
    
    return JsonResponse(response_data)
