from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, TemplateView
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from .models import RAGQuery, RAGConfiguration
from .services import RAGService
import logging

logger = logging.getLogger(__name__)


class RAGHomeView(LoginRequiredMixin, TemplateView):
    """Main RAG interface"""
    template_name = 'rag_app/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_queries'] = RAGQuery.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:5]
        return context


class RAGQueryHistoryView(LoginRequiredMixin, ListView):
    """User's query history"""
    model = RAGQuery
    template_name = 'rag_app/query_history.html'
    context_object_name = 'queries'
    paginate_by = 20
    
    def get_queryset(self):
        return RAGQuery.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


@login_required
def ask_question_view(request):
    """Handle question submission"""
    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        
        if not query:
            messages.error(request, _('الرجاء إدخال سؤال'))
            return redirect('rag-home')
        
        try:
            rag_service = RAGService()
            result = rag_service.ask_question(query, request.user)
            
            context = {
                'query': query,
                'answer': result['answer'],
                'context': result['context'],
                'sources': result['sources']
            }
            
            return render(request, 'rag_app/result.html', context)
            
        except Exception as e:
            logger.error(f"Error in ask_question_view: {e}")
            messages.error(request, _('حدث خطأ أثناء معالجة سؤالك'))
            return redirect('rag-home')
    
    return redirect('rag-home')


@login_required
def search_hadiths_ajax(request):
    """AJAX endpoint for searching hadiths"""
    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        max_results = int(request.POST.get('max_results', 5))
        
        if not query:
            return JsonResponse({'error': 'الرجاء إدخال سؤال'})
        
        try:
            rag_service = RAGService()
            results = rag_service.search_hadiths(query, max_results)
            
            return JsonResponse({
                'query': query,
                'results': results,
                'count': len(results)
            })
            
        except Exception as e:
            logger.error(f"Error in search_hadiths_ajax: {e}")
            return JsonResponse({'error': 'حدث خطأ أثناء البحث'})
    
    return JsonResponse({'error': 'طلب غير صالح'})


def result_view(request):
    """Display RAG query results"""
    query = request.GET.get('query', '')
    answer = request.GET.get('answer', '')
    
    context = {
        'query': query,
        'answer': answer,
        'sources': []  # Will be populated from the stored query
    }
    
    # Try to get the stored query with sources
    if query:
        try:
            stored_query = RAGQuery.objects.filter(query__icontains=query).order_by('-created_at').first()
            if stored_query:
                context['sources'] = stored_query.context_used or []
        except Exception as e:
            logger.error(f"Error retrieving stored query: {e}")
    
    return render(request, 'rag_app/result.html', context)


@permission_required('rag_admin')
def admin_dashboard(request):
    """Admin dashboard for RAG system"""
    try:
        from .services import ChromaDBService
        
        chroma_service = ChromaDBService()
        
        stats = {
            'total_documents': chroma_service.get_document_count(),
            'total_queries': RAGQuery.objects.count(),
            'active_config': RAGConfiguration.objects.filter(is_active=True).first(),
            'recent_queries': RAGQuery.objects.order_by('-created_at')[:10]
        }
        
        return render(request, 'rag_app/admin_dashboard.html', stats)
        
    except Exception as e:
        logger.error(f"Error in admin_dashboard: {e}")
        messages.error(request, _('حدث خطأ أثناء جلب الإحصائيات'))
        return redirect('admin:index')


@permission_required('rag_admin')
def index_hadiths_view(request):
    """Admin view for indexing hadiths"""
    if request.method == 'POST':
        hadith_ids = request.POST.get('hadith_ids', '')
        
        try:
            rag_service = RAGService()
            
            if hadith_ids:
                # Parse comma-separated IDs
                ids = [int(id.strip()) for id in hadith_ids.split(',') if id.strip().isdigit()]
                rag_service.index_hadiths(ids)
                messages.success(request, _(f'تم فهرسة {len(ids)} أحاديث بنجاح'))
            else:
                # Index all hadiths
                rag_service.index_hadiths()
                messages.success(request, _('تم فهرسة جميع الأحاديث بنجاح'))
            
            return redirect('rag-admin-dashboard')
            
        except Exception as e:
            logger.error(f"Error in index_hadiths_view: {e}")
            messages.error(request, _('حدث خطأ أثناء الفهرسة'))
    
    return render(request, 'rag_app/index_hadiths.html')


@permission_required('rag_admin')
def reindex_all_view(request):
    """Re-index all hadiths"""
    if request.method == 'POST':
        try:
            from .services import ChromaDBService
            
            # Clear existing data
            chroma_service = ChromaDBService()
            chroma_service.collection.delete()
            chroma_service._initialize_client()
            
            # Clear Django embeddings
            from .models import DocumentEmbedding
            DocumentEmbedding.objects.all().delete()
            
            # Re-index all hadiths
            rag_service = RAGService()
            rag_service.index_hadiths()
            
            messages.success(request, _('تمت إعادة الفهرسة بنجاح'))
            
        except Exception as e:
            logger.error(f"Error in reindex_all_view: {e}")
            messages.error(request, _('حدث خطأ أثناء إعادة الفهرسة'))
    
    return redirect('rag-admin-dashboard')
