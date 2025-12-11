import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
from chromadb.config import Settings
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.models import User
from hadith_app.models import Hadith, HadithText, Narrator, HadithBook, HadithCategory
from library_app.models import Document
from .models import DocumentEmbedding, RAGConfiguration
from .jais_service import get_jais_service
from .arabic_llm_service import get_arabic_llm_service
from .document_processor import DocumentProcessor
from .utils import suppress_warnings

# Suppress warnings for cleaner output
suppress_warnings()

logger = logging.getLogger(__name__)


class ArabicEmbeddingService:
    """Service for handling Arabic text embeddings"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model"""
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model {self.model_name}: {e}")
            # Fallback to multilingual model
            try:
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                logger.info("Fallback to multilingual embedding model")
            except Exception as e2:
                logger.error(f"Failed to load fallback model: {e2}")
                raise
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts"""
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
        
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error embedding texts: {e}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text"""
        return self.embed_texts([text])[0]


class ChromaDBService:
    """Service for ChromaDB vector database operations"""
    
    def __init__(self, collection_name: str = "hadith_rag"):
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB client"""
        try:
            # Use persistent storage
            persist_directory = getattr(settings, 'CHROMA_DB_PATH', 'chroma_db')
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"ChromaDB initialized with collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to the collection"""
        try:
            ids = [doc['id'] for doc in documents]
            embeddings = [doc['embedding'] for doc in documents]
            texts = [doc['text'] for doc in documents]
            metadatas = [doc.get('metadata', {}) for doc in documents]
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            logger.info(f"Added {len(documents)} documents to ChromaDB")
        except Exception as e:
            logger.error(f"Error adding documents to ChromaDB: {e}")
            raise
    
    def search_similar(self, query_embedding: List[float], n_results: int = 5) -> Dict[str, Any]:
        """Search for similar documents"""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            return results
        except Exception as e:
            logger.error(f"Error searching ChromaDB: {e}")
            raise
    
    def get_document_count(self) -> int:
        """Get total number of documents in collection"""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0


class HadithTextProcessor:
    """Service for processing hadith text for RAG"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        if not text:
            return []
        
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            if chunk_words:
                chunk = ' '.join(chunk_words)
                chunks.append(chunk)
        
        return chunks
    
    def prepare_hadith_documents(self, hadiths: List[Hadith]) -> List[Dict[str, Any]]:
        """Prepare hadith documents for embedding"""
        documents = []
        
        for hadith in hadiths:
            # Main hadith text
            if hadith.text:
                chunks = self.chunk_text(hadith.text)
                for i, chunk in enumerate(chunks):
                    doc = {
                        'id': f"hadith_{hadith.id}_chunk_{i}",
                        'text': chunk,
                        'content_type': 'hadith',
                        'content_id': hadith.id,
                        'metadata': {
                            'hadith_id': str(hadith.id),
                            'source': hadith.source or 'غير معروف',
                            'grade': hadith.grade or '',
                            'chunk_index': str(i),
                            'categories': ','.join([cat.name for cat in hadith.categories.all()])
                        }
                    }
                    documents.append(doc)
            
            # Additional hadith texts
            for hadith_text in hadith.texts.all():
                if hadith_text.text and hadith_text.text != hadith.text:
                    chunks = self.chunk_text(hadith_text.text)
                    for i, chunk in enumerate(chunks):
                        doc = {
                            'id': f"hadith_text_{hadith_text.id}_chunk_{i}",
                            'text': chunk,
                            'content_type': 'hadith_text',
                            'content_id': hadith_text.id,
                            'metadata': {
                                'hadith_id': str(hadith.id),
                                'hadith_text_id': str(hadith_text.id),
                                'source_reference': hadith_text.source_reference or '',
                                'is_primary': str(hadith_text.is_primary),
                                'chunk_index': str(i)
                            }
                        }
                        documents.append(doc)
        
        return documents


class RAGService:
    """Main RAG service for question answering"""
    
    def __init__(self):
        self.embedding_service = ArabicEmbeddingService()
        self.chroma_service = ChromaDBService()
        self.document_processor = DocumentProcessor()
        self.text_processor = HadithTextProcessor()
        self.config = self._get_active_config()
    
    def _get_active_config(self) -> RAGConfiguration:
        """Get active RAG configuration"""
        try:
            return RAGConfiguration.objects.filter(is_active=True).first()
        except Exception as e:
            logger.error(f"Error getting RAG config: {e}")
            # Return default config
            return RAGConfiguration(
                embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                llm_model="aubmindlab/aragpt2-base",
                chunk_size=500,
                chunk_overlap=50,
                max_context=5,
                similarity_threshold=0.7
            )
    
    def index_hadiths(self, hadith_ids: Optional[List[int]] = None):
        """Index hadiths for RAG"""
        try:
            if hadith_ids:
                hadiths = Hadith.objects.filter(id__in=hadith_ids)
            else:
                hadiths = Hadith.objects.all()
            
            logger.info(f"Indexing {hadiths.count()} hadiths")
            
            # Prepare documents
            documents = self.text_processor.prepare_hadith_documents(hadiths)
            
            # Generate embeddings
            texts = [doc['text'] for doc in documents]
            embeddings = self.embedding_service.embed_texts(texts)
            
            # Add embeddings to documents
            for doc, embedding in zip(documents, embeddings):
                doc['embedding'] = embedding
            
            # Store in ChromaDB
            self.chroma_service.add_documents(documents)
            
            # Store in Django DB for backup
            for doc, embedding in zip(documents, embeddings):
                DocumentEmbedding.objects.update_or_create(
                    content_type=doc['content_type'],
                    content_id=doc['content_id'],
                    embedding_model=self.config.embedding_model,
                    defaults={
                        'text_content': doc['text'],
                        'embedding_vector': embedding,
                        'metadata': doc['metadata']
                    }
                )
            
            logger.info(f"Successfully indexed {len(documents)} document chunks")
            
        except Exception as e:
            logger.error(f"Error indexing hadiths: {e}")
            raise
    
    def search_hadiths(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant hadiths"""
        try:
            # Embed the query
            query_embedding = self.embedding_service.embed_text(query)
            
            # Search ChromaDB
            results = self.chroma_service.search_similar(query_embedding, n_results)
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    # Convert distance to similarity score
                    similarity = 1 - distance
                    
                    if similarity >= self.config.similarity_threshold:
                        formatted_results.append({
                            'text': doc,
                            'metadata': metadata,
                            'similarity': similarity,
                            'rank': i + 1
                        })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching hadiths: {e}")
            raise
    
    def generate_answer(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Generate answer using Arabic LLM model with context"""
        try:
            # Get Arabic LLM service
            arabic_llm_service = get_arabic_llm_service()
            
            # Generate response using Arabic LLM
            response = arabic_llm_service.generate_response(query, context)
            
            logger.info("Generated response using Arabic LLM model")
            return response
            
        except Exception as e:
            logger.error(f"Error generating answer with Arabic LLM: {e}")
            # Fallback to template response
            return self._generate_template_response(query, context)
    
    def _generate_template_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Fallback template-based response"""
        context_text = "\n\n".join([
            f"المصدر: {result['metadata'].get('source', 'غير معروف')}\n"
            f"الحديث: {result['text']}\n"
            f"التشابه: {result['similarity']:.2f}"
            for result in context[:3]
        ])
        
        return f"""بناءً على البحث في قاعدة البيانات، إليك الأحاديث ذات الصلة بسؤالك "{query}":

{context_text}

ملاحظة: هذه إجابة قائمة على البحث الدلالي. يرجى التحقق من الأحاديث ومصادرها."""
    
    def index_library_documents(self, document_ids: Optional[List[int]] = None):
        """Index library documents for RAG"""
        try:
            if document_ids:
                documents = Document.objects.filter(id__in=document_ids, is_public=True)
            else:
                documents = self.document_processor.get_all_library_documents()
            
            logger.info(f"Indexing {documents.count()} library documents")
            
            # Prepare documents
            processed_docs = self.document_processor.prepare_library_documents(documents)
            
            if not processed_docs:
                logger.warning("No library documents processed")
                return
            
            # Generate embeddings
            texts = [doc['text'] for doc in processed_docs]
            embeddings = self.embedding_service.embed_texts(texts)
            
            # Add embeddings to documents
            for doc, embedding in zip(processed_docs, embeddings):
                doc['embedding'] = embedding
            
            # Store in ChromaDB
            self.chroma_service.add_documents(processed_docs)
            
            # Store in Django DB for backup
            for doc, embedding in zip(processed_docs, embeddings):
                DocumentEmbedding.objects.update_or_create(
                    content_type='library_document',
                    content_id=doc['metadata']['document_id'],
                    embedding_model=self.config.embedding_model,
                    defaults={
                        'text_content': doc['text'],
                        'embedding_vector': embedding,
                        'metadata': doc['metadata']
                    }
                )
            
            logger.info(f"Successfully indexed {len(processed_docs)} library document chunks")
            
        except Exception as e:
            logger.error(f"Error indexing library documents: {e}")
            raise
    
    def index_all_content(self):
        """Index both hadiths and library documents"""
        try:
            logger.info("Starting comprehensive indexing of all content")
            
            # Index hadiths
            self.index_hadiths()
            
            # Index library documents
            self.index_library_documents()
            
            total_docs = self.chroma_service.get_document_count()
            logger.info(f"Comprehensive indexing completed. Total documents: {total_docs}")
            
        except Exception as e:
            logger.error(f"Error in comprehensive indexing: {e}")
            raise
    
    def ask_question(self, query: str, user: Optional[User] = None) -> Dict[str, Any]:
        """Main RAG endpoint for asking questions"""
        try:
            # Search for relevant hadiths
            search_results = self.search_hadiths(query, self.config.max_context)
            
            if not search_results:
                return {
                    'query': query,
                    'answer': 'لم يتم العثور على أحاديث ذات صلة بسؤالك. يرجى محاولة صياغة السؤال بشكل مختلف.',
                    'context': [],
                    'sources': []
                }
            
            # Generate answer
            answer = self.generate_answer(query, search_results)
            
            # Extract sources
            sources = []
            for result in search_results:
                metadata = result['metadata']
                source_info = {
                    'hadith_id': metadata.get('hadith_id'),
                    'source': metadata.get('source', 'غير معروف'),
                    'grade': metadata.get('grade'),
                    'similarity': result['similarity']
                }
                sources.append(source_info)
            
            # Store query in database
            from .models import RAGQuery
            RAGQuery.objects.create(
                user=user,
                query=query,
                response=answer,
                context_used=search_results,
                embedding_model=self.config.embedding_model,
                llm_model=self.config.llm_model
            )
            
            return {
                'query': query,
                'answer': answer,
                'context': search_results,
                'sources': sources
            }
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return {
                'query': query,
                'answer': 'حدث خطأ أثناء معالجة سؤالك. يرجى المحاولة مرة أخرى.',
                'context': [],
                'sources': [],
                'error': str(e)
            }
