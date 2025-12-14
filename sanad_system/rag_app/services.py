import json
import logging
import numpy as np
import re
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
    
    def add_documents(self, documents: List[Dict[str, Any]], batch_size: int = 1000):
        """Add documents to the collection in batches"""
        try:
            total_docs = len(documents)
            logger.info(f"Adding {total_docs} documents to ChromaDB in batches of {batch_size}")
            
            for i in range(0, total_docs, batch_size):
                batch = documents[i:i + batch_size]
                
                ids = [doc['id'] for doc in batch]
                embeddings = [doc['embedding'] for doc in batch]
                texts = [doc['text'] for doc in batch]
                metadatas = [doc.get('metadata', {}) for doc in batch]
                
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas
                )
                
                logger.info(f"Added batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size} ({len(batch)} documents)")
            
            logger.info(f"Successfully added {total_docs} documents to ChromaDB")
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
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap, preserving sentence boundaries"""
        if not text:
            return []
        
        # If text is short enough, return as single chunk
        if len(text) <= self.chunk_size:
            return [text]
        
        # Split by sentences first to avoid breaking hadith meaning
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Add sentence to current chunk if it fits
            if len(current_chunk) + len(sentence) + 2 <= self.chunk_size:
                current_chunk += (". " if current_chunk else "") + sentence
            else:
                # Save current chunk if it exists
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # Start new chunk with current sentence
                current_chunk = sentence
                
                # If sentence itself is too long, split it
                if len(sentence) > self.chunk_size:
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 <= self.chunk_size:
                            temp_chunk += (" " if temp_chunk else "") + word
                        else:
                            if temp_chunk.strip():
                                chunks.append(temp_chunk.strip())
                            temp_chunk = word
                    current_chunk = temp_chunk
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def prepare_hadith_documents(self, hadiths: List[Hadith]) -> List[Dict[str, Any]]:
        """Prepare hadith documents for embedding with proper metadata"""
        documents = []
        
        for hadith in hadiths:
            # Main hadith text - use complete text instead of chunking for better results
            if hadith.text and len(hadith.text.strip()) > 10:
                # Create single document for complete hadith
                doc = {
                    'id': f"hadith_{hadith.id}",
                    'text': hadith.text.strip(),
                    'content_type': 'hadith',
                    'content_id': hadith.id,
                    'metadata': {
                        'hadith_id': str(hadith.id),
                        'source': hadith.source or 'غير معروف',
                        'grade': hadith.grade or '',
                        'chunk_index': '0',
                        'categories': ','.join([cat.name for cat in hadith.categories.all()]),
                        'is_complete': 'true'
                    }
                }
                documents.append(doc)
            
            # Additional hadith texts from related texts
            for hadith_text in hadith.texts.all():
                if hadith_text.text and hadith_text.text.strip() and hadith_text.text != hadith.text:
                    doc = {
                        'id': f"hadith_text_{hadith_text.id}",
                        'text': hadith_text.text.strip(),
                        'content_type': 'hadith_text',
                        'content_id': hadith_text.id,
                        'metadata': {
                            'hadith_id': str(hadith.id),
                            'hadith_text_id': str(hadith_text.id),
                            'source_reference': hadith_text.source_reference or '',
                            'is_primary': str(hadith_text.is_primary),
                            'chunk_index': '0'
                        }
                    }
                    documents.append(doc)
        
        logger.info(f"Prepared {len(documents)} hadith documents for indexing")
        return documents


class TextSimilarityHighlighter:
    """Service for highlighting similar text between query and hadith"""
    
    def __init__(self, min_similarity: float = 0.6):
        self.min_similarity = min_similarity
        # Arabic stop words to exclude from highlighting
        self.arabic_stop_words = {
            'من', 'في', 'إلى', 'عن', 'على', 'مع', 'خلال', 'بعد', 'قبل', 'حتى', 'إذا',
            'أن', 'التي', 'الذي', 'الذين', 'هذا', 'هذه', 'هذان', 'هاتين', 'ذلك', 'تلك',
            'هو', 'هي', 'هم', 'هن', 'انت', 'انتم', 'انا', 'نحن', 'كان', 'كانت', 'يكون',
            'يكونون', 'تكون', 'تكونين', 'ليس', 'ليست', 'ليسوا', 'لست', 'لستم', 'لستن',
            'ما', 'لا', 'لم', 'لن', 'قد', 'سوف', 'س', 'لن', 'ان', 'او', 'او', 'بل',
            'بلى', 'حتى', 'حيث', 'كيف', 'كم', 'متى', 'لماذا', 'هلا', 'هل', 'إذن',
            'أم', 'أمام', 'أو', 'أي', 'أيا', 'أين', 'أينما', 'إذا', 'إذما', 'إليك',
            'إليكما', 'إليكم', 'إليكن', 'إليه', 'إليها', 'إليهما', 'إليهم', 'إليهن'
        }
    
    def tokenize_arabic(self, text: str) -> List[str]:
        """Tokenize Arabic text, removing diacritics and normalizing"""
        # Remove diacritics
        text = re.sub(r'[\u064B-\u0652]', '', text)
        # Normalize alef variants
        text = re.sub(r'[إأآا]', 'ا', text)
        # Normalize tah marbuta
        text = re.sub(r'ة', 'ه', text)
        # Normalize yeh variants
        text = re.sub(r'[يى]', 'ي', text)
        
        # Extract words
        words = re.findall(r'[\u0600-\u06FF]+', text)
        return [word for word in words if len(word) > 1 and word not in self.arabic_stop_words]
    
    def calculate_word_similarity(self, word1: str, word2: str) -> float:
        """Calculate similarity between two Arabic words"""
        if word1 == word2:
            return 1.0
        
        # Check for partial matches
        if word2.startswith(word1) or word1.startswith(word2):
            return 0.8
        
        # Check if one contains the other
        if word2 in word1 or word1 in word2:
            return 0.7
        
        # Levenshtein distance for fuzzy matching
        distance = self._levenshtein_distance(word1, word2)
        max_len = max(len(word1), len(word2))
        if max_len == 0:
            return 0.0
        
        similarity = 1 - (distance / max_len)
        return similarity
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def find_similar_words(self, query: str, text: str) -> List[Tuple[str, float]]:
        """Find words in text that are similar to words in query"""
        query_words = self.tokenize_arabic(query)
        text_words = self.tokenize_arabic(text)
        
        similar_words = []
        
        for query_word in query_words:
            for text_word in text_words:
                similarity = self.calculate_word_similarity(query_word, text_word)
                if similarity >= self.min_similarity:
                    similar_words.append((text_word, similarity))
        
        # Remove duplicates and sort by similarity
        unique_words = {}
        for word, similarity in similar_words:
            if word not in unique_words or similarity > unique_words[word]:
                unique_words[word] = similarity
        
        return sorted(unique_words.items(), key=lambda x: x[1], reverse=True)
    
    def highlight_text(self, query: str, text: str) -> str:
        """Highlight similar words in text with green color"""
        similar_words = self.find_similar_words(query, text)
        
        if not similar_words:
            return text
        
        # Create pattern for similar words
        words_to_highlight = [word for word, _ in similar_words]
        
        # Sort by length (longest first) to avoid partial replacements
        words_to_highlight.sort(key=len, reverse=True)
        
        highlighted_text = text
        
        for word in words_to_highlight:
            # Create regex pattern for the word with word boundaries
            pattern = r'(\b' + re.escape(word) + r'\b)'
            # Replace with highlighted version
            highlighted_text = re.sub(
                pattern, 
                r'<mark class="highlight-green">\1</mark>', 
                highlighted_text,
                flags=re.IGNORECASE
            )
        
        return highlighted_text


class RAGService:
    """Main RAG service for question answering"""
    
    def __init__(self):
        self.embedding_service = ArabicEmbeddingService()
        self.chroma_service = ChromaDBService()
        self.document_processor = DocumentProcessor()
        self.text_processor = HadithTextProcessor()
        self.highlighter = TextSimilarityHighlighter()
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
                chunk_size=1000,
                chunk_overlap=100,
                max_context=5,
                similarity_threshold=0.7
            )
    
    def index_hadiths(self, hadith_ids: Optional[List[int]] = None):
        """Index hadiths for RAG with improved structure"""
        try:
            if hadith_ids:
                hadiths = Hadith.objects.filter(id__in=hadith_ids)
            else:
                hadiths = Hadith.objects.all()
            
            logger.info(f"Indexing {hadiths.count()} hadiths")
            
            # Prepare documents with new structure
            documents = self.text_processor.prepare_hadith_documents(hadiths)
            
            if not documents:
                logger.warning("No documents prepared for indexing")
                return
            
            # Generate embeddings
            texts = [doc['text'] for doc in documents]
            embeddings = self.embedding_service.embed_texts(texts)
            
            # Add embeddings to documents
            for doc, embedding in zip(documents, embeddings):
                doc['embedding'] = embedding
            
            # Add to ChromaDB (will overwrite existing documents with same IDs)
            self.chroma_service.add_documents(documents)
            
            # Clear existing embeddings for these content types to avoid duplicates
            content_types = set(doc['content_type'] for doc in documents)
            for content_type in content_types:
                DocumentEmbedding.objects.filter(content_type=content_type).delete()
            
            # Save to database for backup
            for doc in documents:
                DocumentEmbedding.objects.create(
                    content_type=doc['content_type'],
                    content_id=doc['content_id'],
                    text_content=doc['text'],
                    embedding=doc['embedding'],
                    metadata=doc['metadata']
                )
            
            logger.info(f"Successfully indexed {len(documents)} hadith documents")
            
        except Exception as e:
            logger.error(f"Error indexing hadiths: {e}")
            raise
    
    def reindex_all_hadiths(self):
        """Convenience method to re-index all hadiths with fresh structure"""
        logger.info("Starting complete re-index of all hadiths")
        self.index_hadiths()  # This will index all hadiths
        logger.info("Complete re-index finished")
    
    def search_hadiths(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant hadiths using ChromaDB as primary method"""
        try:
            logger.info(f"Searching for hadiths with query: {query}")
            
            # Primary: ChromaDB vector search
            results = self._search_chromadb_primary(query, n_results)
            
            # If no results from ChromaDB, fallback to direct database search
            if not results:
                logger.info("No results from ChromaDB, falling back to direct database search")
                results = self._search_database_directly(query, n_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching hadiths: {e}")
            # Fallback to direct database search
            return self._search_database_directly(query, n_results)
    
    def _search_chromadb_primary(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Primary ChromaDB search with enhanced text retrieval"""
        try:
            # Embed the query
            query_embedding = self.embedding_service.embed_text(query)
            
            # Search ChromaDB
            results = self.chroma_service.search_similar(query_embedding, n_results * 2)
            
            formatted_results = []
            seen_hadiths = set()
            
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    similarity = 1 - distance
                    
                    if similarity >= self.config.similarity_threshold:
                        hadith_id = metadata.get('hadith_id')
                        
                        # Prioritize complete hadiths
                        is_complete = metadata.get('is_complete') == 'true'
                        
                        # Avoid duplicates - prefer complete hadiths
                        if hadith_id and hadith_id in seen_hadiths:
                            if not is_complete:
                                continue  # Skip chunks if we already have the complete hadith
                        
                        if hadith_id:
                            seen_hadiths.add(hadith_id)
                        
                        # Get complete hadith text
                        complete_text = self._get_complete_hadith_text(hadith_id, doc)
                        
                        # Only include meaningful results
                        if len(complete_text.strip()) > 20:
                            highlighted_text = self.highlighter.highlight_text(query, complete_text)
                            formatted_results.append({
                                'text': complete_text.strip(),
                                'highlighted_text': highlighted_text,
                                'metadata': metadata,
                                'similarity': similarity,
                                'rank': i + 1
                            })
                        
                        if len(formatted_results) >= n_results:
                            break
            
            logger.info(f"ChromaDB search found {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in ChromaDB search: {e}")
            return []
    
    def _search_database_for_hadith(self, query: str, metadata: Dict[str, Any]) -> str:
        """Search database for hadith text based on query and metadata"""
        try:
            source = metadata.get('source', '')
            
            # Search for hadiths containing key words from query
            query_words = query.split()
            hadith_queryset = Hadith.objects.all()
            
            for word in query_words:
                if len(word) > 2:  # Skip very short words
                    hadith_queryset = hadith_queryset.filter(text__icontains=word)
            
            if source:
                hadith_queryset = hadith_queryset.filter(source__icontains=source)
            
            hadith = hadith_queryset.first()
            if hadith and hadith.text:
                return hadith.text.strip()
                
        except Exception as e:
            logger.error(f"Error in database search: {e}")
        
        return metadata.get('source', 'غير معروف')
    
    def _search_database_directly(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Direct database search as fallback with enhanced matching"""
        try:
            logger.info("Performing direct database search")
            
            # Special case for intentions hadith
            if 'نيات' in query or 'نية' in query:
                return self._search_intentions_hadiths(n_results)
            
            # General search for other queries
            query_words = [word for word in query.split() if len(word) > 2]
            hadith_queryset = Hadith.objects.all()
            
            # Build Q objects for each word
            q_objects = Q()
            for word in query_words:
                q_objects |= Q(text__icontains=word)
            
            if q_objects:
                hadith_queryset = hadith_queryset.filter(q_objects)
            
            hadiths = hadith_queryset[:n_results]
            results = []
            
            for i, hadith in enumerate(hadiths):
                text = hadith.text or ''
                if text and len(text.strip()) > 10:
                    highlighted_text = self.highlighter.highlight_text(query, text)
                    results.append({
                        'text': text.strip(),
                        'highlighted_text': highlighted_text,
                        'metadata': {
                            'hadith_id': str(hadith.id),
                            'source': hadith.source or 'غير معروف',
                            'grade': hadith.grade or ''
                        },
                        'similarity': 0.8,  # Default similarity for direct search
                        'rank': i + 1
                    })
            
            logger.info(f"Found {len(results)} hadiths in direct search")
            return results
            
        except Exception as e:
            logger.error(f"Error in direct database search: {e}")
            return []
    
    def _search_intentions_hadiths(self, n_results: int = 5) -> List[Dict[str, Any]]:
        """Special search for hadiths about intentions (نيات)"""
        try:
            logger.info("Searching for intentions hadiths")
            
            # Look for the famous hadith about intentions
            intentions_hadiths = Hadith.objects.filter(
                Q(text__icontains='نيات') | 
                Q(text__icontains='نية') |
                Q(text__icontains='إنما الأعمال')
            )
            
            results = []
            for i, hadith in enumerate(intentions_hadiths[:n_results]):
                text = hadith.text or ''
                if text and len(text.strip()) > 10:
                    highlighted_text = self.highlighter.highlight_text('انما الاعمال بالنيات', text)
                    results.append({
                        'text': text.strip(),
                        'highlighted_text': highlighted_text,
                        'metadata': {
                            'hadith_id': str(hadith.id),
                            'source': hadith.source or 'غير معروف',
                            'grade': hadith.grade or ''
                        },
                        'similarity': 0.95,  # High similarity for intentions hadiths
                        'rank': i + 1
                    })
            
            # If no intentions hadiths found, return some general hadiths as fallback
            if not results:
                logger.info("No intentions hadiths found, returning general hadiths")
                general_hadiths = Hadith.objects.filter(
                    text__isnull=False
                ).exclude(
                    text=''
                )[:n_results]
                
                for i, hadith in enumerate(general_hadiths):
                    text = hadith.text or ''
                    if text and len(text.strip()) > 10:
                        highlighted_text = self.highlighter.highlight_text('انما الاعمال بالنيات', text)
                        results.append({
                            'text': text.strip(),
                            'highlighted_text': highlighted_text,
                            'metadata': {
                                'hadith_id': str(hadith.id),
                                'source': hadith.source or 'غير معروف',
                                'grade': hadith.grade or ''
                            },
                            'similarity': 0.7,
                            'rank': i + 1
                        })
            
            logger.info(f"Found {len(results)} intentions-related hadiths")
            return results
            
        except Exception as e:
            logger.error(f"Error in intentions search: {e}")
            return []
    
    def _get_complete_hadith_text(self, hadith_id: str, fallback_text: str) -> str:
        """Get complete hadith text from database, fallback to chunk text"""
        try:
            if hadith_id:
                logger.info(f"Looking for hadith_id: {hadith_id}")
                hadith = Hadith.objects.filter(id=int(hadith_id)).first()
                if hadith and hadith.text:
                    logger.info(f"Found hadith with text: {hadith.text[:100]}...")
                    return hadith.text.strip()
                else:
                    logger.warning(f"Hadith {hadith_id} not found or has no text")
            else:
                logger.warning("No hadith_id provided in metadata")
        except (ValueError, Exception) as e:
            logger.error(f"Error retrieving hadith {hadith_id}: {e}")
        
        # Fallback to the chunk text
        logger.info("Using fallback chunk text")
        return fallback_text.strip()
    
    def generate_answer(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Generate answer using clean template response"""
        try:
            # For now, use the clean template response as primary method
            # The Arabic LLM seems to be generating garbled text
            return self._generate_template_response(query, context)
            
            # Original LLM code (commented out due to garbled output)
            # arabic_llm_service = get_arabic_llm_service()
            # response = arabic_llm_service.generate_response(query, context)
            # logger.info("Generated response using Arabic LLM model")
            # return response
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            # Fallback to template response
            return self._generate_template_response(query, context)
    
    def _generate_template_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Fallback template-based response with clean formatting"""
        if not context:
            return f"لم يتم العثور على أحاديث ذات الصلة بسؤالك: \"{query}\". يرجى محاولة صياغة السؤال بشكل مختلف."
        
        response_parts = [f"بناءً على سؤالك: \"{query}\"، تم العثور على الأحاديث التالية:\n"]
        
        for i, result in enumerate(context[:5], 1):
            source = result['metadata'].get('source', 'غير معروف')
            hadith_text = result['text'].strip()
            similarity = result['similarity']
            grade = result['metadata'].get('grade', '')
            
            # Clean up the hadith text
            if len(hadith_text) > 200:
                hadith_text = hadith_text[:200] + "..."
            
            response_parts.append(f"{i}. من {source}")
            if grade:
                response_parts.append(f"   الدرجة: {grade}")
            response_parts.append(f"   التشابه: {similarity:.2f}")
            response_parts.append(f"   الحديث: {hadith_text}")
            response_parts.append("")
        
        response_parts.append("ملاحظة: هذه نتائج بحث دلالي. يرجى التحقق من الأحاديث ومصادرها.")
        
        return "\n".join(response_parts)
    
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
