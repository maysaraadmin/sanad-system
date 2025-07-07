from django.http import JsonResponse
from django.db.models import Q
from django.utils.translation import gettext as _
from django.core.paginator import Paginator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from library.models import Document, DocumentCategory


class DocumentSuggestionsAPIView(APIView):
    """
    API endpoint to provide document search suggestions.
    """
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        if not query:
            return Response({
                'suggestions': []
            }, status=status.HTTP_200_OK)
        
        # Search in title, description, and content
        documents = Document.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(content__icontains=query),
            is_public=True
        ).select_related('category').order_by('-created_at')
        
        # Apply additional filters if provided
        category_id = request.GET.get('category')
        if category_id:
            documents = documents.filter(category_id=category_id)
            
        file_type = request.GET.get('file_type')
        if file_type:
            documents = documents.filter(file_type=file_type)
        
        # Limit the number of suggestions
        documents = documents[:10]
        
        # Format the suggestions
        suggestions = [{
            'title': doc.title,
            'description': doc.description[:150] + '...' if doc.description else '',
            'url': doc.get_absolute_url(),
            'type': 'document',
            'score': 1.0  # Simple scoring for now
        } for doc in documents]
        
        # Add category suggestions if no or few document matches
        if len(suggestions) < 5:
            categories = DocumentCategory.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )[:5]
            
            for category in categories:
                suggestions.append({
                    'title': category.name,
                    'description': _('Category: ') + (category.description[:120] + '...' if category.description else ''),
                    'url': category.get_absolute_url(),
                    'type': 'category',
                    'score': 0.8  # Slightly lower score than direct document matches
                })
        
        # Sort by score (highest first)
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        
        return Response({
            'query': query,
            'suggestions': suggestions[:10]  # Return at most 10 suggestions
        })


def document_search_api(request):
    """
    Legacy API endpoint for document search (kept for backward compatibility).
    """
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))
    
    documents = Document.objects.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(content__icontains=query),
        is_public=True
    ).select_related('category').order_by('-created_at')
    
    # Apply filters
    category_id = request.GET.get('category')
    if category_id:
        documents = documents.filter(category_id=category_id)
        
    file_type = request.GET.get('file_type')
    if file_type:
        documents = documents.filter(file_type=file_type)
    
    # Paginate results
    paginator = Paginator(documents, per_page)
    page_obj = paginator.get_page(page)
    
    results = [{
        'id': doc.id,
        'title': doc.title,
        'description': doc.description,
        'url': doc.get_absolute_url(),
        'file_type': doc.get_file_type_display(),
        'category': {
            'id': doc.category.id,
            'name': doc.category.name,
            'url': doc.category.get_absolute_url()
        } if doc.category else None,
        'created_at': doc.created_at.isoformat(),
        'updated_at': doc.updated_at.isoformat()
    } for doc in page_obj]
    
    return JsonResponse({
        'query': query,
        'total': paginator.count,
        'page': page_obj.number,
        'pages': paginator.num_pages,
        'per_page': per_page,
        'results': results
    })
