from rest_framework import serializers, status, viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from .models import RAGQuery, DocumentEmbedding, RAGConfiguration
from .services import RAGService
import logging

logger = logging.getLogger(__name__)


class RAGQuerySerializer(serializers.ModelSerializer):
    """Serializer for RAG queries"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = RAGQuery
        fields = [
            'id', 'user', 'user_name', 'query', 'response', 
            'context_used', 'embedding_model', 'llm_model', 
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DocumentEmbeddingSerializer(serializers.ModelSerializer):
    """Serializer for document embeddings"""
    
    class Meta:
        model = DocumentEmbedding
        fields = [
            'id', 'content_type', 'content_id', 'text_content',
            'embedding_model', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RAGConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for RAG configuration"""
    
    class Meta:
        model = RAGConfiguration
        fields = [
            'id', 'name', 'embedding_model', 'llm_model',
            'chunk_size', 'chunk_overlap', 'max_context',
            'similarity_threshold', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AskQuestionSerializer(serializers.Serializer):
    """Serializer for asking questions"""
    query = serializers.CharField(max_length=1000)
    max_results = serializers.IntegerField(default=5, min_value=1, max_value=20)


class AskQuestionView(APIView):
    """API endpoint for asking RAG questions"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Ask a question and get RAG response"""
        try:
            serializer = AskQuestionSerializer(data=request.data)
            if serializer.is_valid():
                query = serializer.validated_data['query']
                max_results = serializer.validated_data.get('max_results', 5)
                
                # Get RAG service
                rag_service = RAGService()
                
                # Process the question
                result = rag_service.ask_question(
                    query=query,
                    user=request.user if request.user.is_authenticated else None
                )
                
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error in AskQuestionView: {e}")
            return Response(
                {'error': 'حدث خطأ أثناء معالجة السؤال'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SearchHadithsView(APIView):
    """API endpoint for searching hadiths"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Search hadiths using semantic search"""
        try:
            serializer = AskQuestionSerializer(data=request.data)
            if serializer.is_valid():
                query = serializer.validated_data['query']
                max_results = serializer.validated_data.get('max_results', 5)
                
                # Get RAG service
                rag_service = RAGService()
                
                # Search hadiths
                results = rag_service.search_hadiths(query, max_results)
                
                return Response({
                    'query': query,
                    'results': results,
                    'count': len(results)
                }, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error in SearchHadithsView: {e}")
            return Response(
                {'error': 'حدث خطأ أثناء البحث'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IndexHadithsView(APIView):
    """API endpoint for indexing hadiths"""
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        """Index hadiths for RAG"""
        try:
            hadith_ids = request.data.get('hadith_ids', None)
            
            # Get RAG service
            rag_service = RAGService()
            
            # Index hadiths
            rag_service.index_hadiths(hadith_ids)
            
            return Response({
                'message': 'تم فهرسة الأحاديث بنجاح',
                'hadith_ids': hadith_ids
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in IndexHadithsView: {e}")
            return Response(
                {'error': 'حدث خطأ أثناء الفهرسة'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RAGQueryViewSet(viewsets.ModelViewSet):
    """ViewSet for RAG queries"""
    queryset = RAGQuery.objects.all()
    serializer_class = RAGQuerySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Filter queries by user if not admin"""
        if self.request.user.is_staff:
            return RAGQuery.objects.all()
        return RAGQuery.objects.filter(user=self.request.user)


class RAGConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for RAG configurations"""
    queryset = RAGConfiguration.objects.all()
    serializer_class = RAGConfigurationSerializer
    permission_classes = [permissions.IsAdminUser]


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def rag_stats(request):
    """Get RAG system statistics"""
    try:
        from .services import ChromaDBService
        
        chroma_service = ChromaDBService()
        
        stats = {
            'total_documents': chroma_service.get_document_count(),
            'total_queries': RAGQuery.objects.count(),
            'active_config': RAGConfiguration.objects.filter(is_active=True).first(),
            'recent_queries': RAGQuery.objects.order_by('-created_at')[:10].values(
                'id', 'query', 'created_at', 'user__username'
            )
        }
        
        # Serialize active config
        if stats['active_config']:
            stats['active_config'] = RAGConfigurationSerializer(stats['active_config']).data
        
        return Response(stats)
        
    except Exception as e:
        logger.error(f"Error in rag_stats: {e}")
        return Response(
            {'error': 'حدث خطأ أثناء جلب الإحصائيات'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def reindex_all(request):
    """Re-index all hadiths"""
    try:
        from .services import ChromaDBService
        
        # Clear existing data
        chroma_service = ChromaDBService()
        chroma_service.collection.delete()
        chroma_service._initialize_client()
        
        # Clear Django embeddings
        DocumentEmbedding.objects.all().delete()
        
        # Re-index all hadiths
        rag_service = RAGService()
        rag_service.index_hadiths()
        
        return Response({
            'message': 'تمت إعادة الفهرسة بنجاح',
            'total_documents': chroma_service.get_document_count()
        })
        
    except Exception as e:
        logger.error(f"Error in reindex_all: {e}")
        return Response(
            {'error': 'حدث خطأ أثناء إعادة الفهرسة'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
