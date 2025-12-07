from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .document_processor import process_document
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.conf import settings
import mimetypes
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor
import html
import os

from .models import Document, DocumentType
from .forms import DocumentForm, DocumentTypeForm

class DocumentListView(ListView):
    model = Document
    template_name = 'library_app/document_list.html'
    context_object_name = 'documents'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Only show public documents to non-logged in users
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        
        # Filter by document type if provided
        document_type = self.request.GET.get('type')
        if document_type:
            queryset = queryset.filter(document_type__id=document_type)
        
        return queryset.order_by('-uploaded_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document_types'] = DocumentType.objects.all()
        return context

class DocumentDetailView(DetailView):
    model = Document
    template_name = 'library_app/document_detail.html'
    context_object_name = 'document'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Only allow access to public documents for non-logged in users
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        return queryset
    
    def get(self, request, *args, **kwargs):
        # Ensure this always returns the template, never downloads the file
        response = super().get(request, *args, **kwargs)
        # Set content type to HTML to prevent browser from treating it as file download
        response['Content-Type'] = 'text/html; charset=utf-8'
        return response

@login_required
def document_view(request, pk):
    document = get_object_or_404(Document, pk=pk)
    
    # Check permissions
    if not document.is_public and document.uploaded_by != request.user:
        raise PermissionDenied
    
    # Get the file path
    file_path = document.file.path
    
    # Get the content type
    content_type = mimetypes.guess_type(file_path)[0]
    
    # Create the file response
    response = FileResponse(
        open(file_path, 'rb'),
        content_type=content_type,
        as_attachment=False
    )
    
    # Add headers for PDF viewing in browser
    if content_type == 'application/pdf':
        response['Content-Disposition'] = 'inline; filename="{}.pdf"'.format(document.title)
        response['Accept-Ranges'] = 'bytes'
    
    return response

@login_required
def word_to_html(request, pk):
    document = get_object_or_404(Document, pk=pk)
    
    # Check permissions
    if not document.is_public and document.uploaded_by != request.user:
        raise PermissionDenied
    
    # Get the file path
    file_path = document.file.path
    
    # Read the Word document
    doc = docx.Document(file_path)
    
    # Create HTML content
    html_content = '<div class="word-document">'
    
    # Process paragraphs
    for para in doc.paragraphs:
        # Get paragraph style
        style = para.style.name.lower()
        
        # Determine HTML tag based on style
        if style == 'heading 1':
            tag = 'h1'
        elif style == 'heading 2':
            tag = 'h2'
        elif style == 'heading 3':
            tag = 'h3'
        else:
            tag = 'p'
        
        # Add paragraph content
        html_content += f'<{tag} class="word-{style}">'
        
        # Process runs
        for run in para.runs:
            text = html.escape(run.text)
            
            # Add styling
            style_class = []
            if run.bold:
                style_class.append('bold')
            if run.italic:
                style_class.append('italic')
            if run.underline:
                style_class.append('underline')
            
            if style_class:
                text = f'<span class="word-{" ".join(style_class)}">{text}</span>'
            
            html_content += text
        
        html_content += f'</{tag}>'
    
    html_content += '</div>'
    
    # Return HTML response
    return HttpResponse(html_content, content_type='text/html')

class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'library_app/document_form.html'
    success_url = reverse_lazy('library_app:document_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document_types'] = DocumentType.objects.all()
        return context
    
    def form_valid(self, form):
        try:
            form.instance.uploaded_by = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, _('تم رفع المستند بنجاح'))
            return response
        except Exception as e:
            messages.error(self.request, _('حدث خطأ أثناء رفع المستند: %s') % str(e))
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('هناك أخطاء في النموذج. يرجى التأكد من ملء جميع الحقول بشكل صحيح.'))
        return super().form_invalid(form)

class DocumentUpdateView(LoginRequiredMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = 'library_app/document_form.html'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Only allow updating own documents
        return queryset.filter(uploaded_by=self.request.user)
    
    def get_success_url(self):
        messages.success(self.request, _('تم تحديث المستند بنجاح'))
        return reverse_lazy('library_app:document_detail', kwargs={'pk': self.object.pk})

class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = Document
    template_name = 'library_app/document_confirm_delete.html'
    success_url = reverse_lazy('library_app:document_list')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Only allow deleting own documents
        return queryset.filter(uploaded_by=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تم حذف المستند بنجاح'))
        return super().delete(request, *args, **kwargs)

class DocumentTypeCreateView(LoginRequiredMixin, CreateView):
    model = DocumentType
    form_class = DocumentTypeForm
    template_name = 'library_app/document_type_form.html'
    success_url = reverse_lazy('library_app:document_type_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('تم إضافة نوع المستند بنجاح'))
        return super().form_valid(form)

class DocumentTypeListView(LoginRequiredMixin, ListView):
    model = DocumentType
    template_name = 'library_app/document_type_list.html'
    context_object_name = 'document_types'
    paginate_by = 20

@login_required
@require_POST
def toggle_public(request, pk):
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
    document.is_public = not document.is_public
    document.save()
    return JsonResponse({'status': 'success', 'is_public': document.is_public})

@login_required
def process_document_view(request, pk):
    """View to process a document and extract hadith/narrator information"""
    document = get_object_or_404(Document, pk=pk)
    
    # Check permissions
    if not document.is_public and document.uploaded_by != request.user:
        raise PermissionDenied
    
    results = None
    error_message = None
    debug_info = {}
    
    # Process the document if this is a POST request or if we have analysis parameters
    if request.method == 'POST' or 'analyze' in request.GET or 'debug' in request.GET:
        try:
            from .document_processor import process_document
            
            # Process the document
            results = process_document(document)
            
            # Check if we got any results
            if not results:
                error_message = 'لم يتم العثور على أي نتائج من معالجة المستند'
                messages.warning(request, error_message)
            elif 'error' in results:
                error_message = results.get('error', 'حدث خطأ غير معروف')
                messages.error(request, error_message)
                if 'debug' in results:
                    debug_info = results['debug']
            else:
                messages.success(request, 'تم تحليل المستند بنجاح')
                
                # Add some debug info to results
                if 'debug' in results and 'debug' in request.GET:
                    debug_info = results.pop('debug')
                
        except ImportError as e:
            error_message = f'خطأ في استيراد المكتبات المطلوبة: {str(e)}. تأكد من تثبيت python-docx و PyPDF2'
            messages.error(request, error_message)
        except Exception as e:
            import traceback
            error_message = f'حدث خطأ أثناء تحليل المستند: {str(e)}'
            messages.error(request, error_message)
            debug_info = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    context = {
        'document': document,
        'results': results,
        'title': f'تحليل المستند: {document.title}',
        'error_message': error_message,
        'debug_info': debug_info,
        'show_debug': 'debug' in request.GET
    }
    
    return render(request, 'library_app/document_analysis.html', context)

def pdf_viewer(request, pk):
    """Custom PDF viewer using Django template"""
    document = get_object_or_404(Document, pk=pk)
    
    # Check permissions
    if not document.is_public and document.uploaded_by != request.user:
        raise PermissionDenied
        
    context = {
        'document': document,
        'file_url': document.file.url
    }
    return render(request, 'library_app/pdf_viewer.html', context)
