"""
Document processing service for RAG system
Handles text extraction from library documents for indexing
"""

import logging
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import PyPDF2
import docx
from django.conf import settings
from library_app.models import Document

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Service for processing library documents for RAG indexing"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.doc', '.txt']
        self.document_analyzer = None
        self._init_document_analyzer()
    
    def _init_document_analyzer(self):
        """Initialize simple OCR service for PDF processing"""
        try:
            # Import our simple OCR service
            from .simple_ocr import SimpleOCRService
            self.document_analyzer = SimpleOCRService()
            logger.info("SimpleOCRService initialized for RAG processing")
        except ImportError:
            logger.warning("SimpleOCRService not available, using fallback")
            self.document_analyzer = None
        except Exception as e:
            logger.error(f"Failed to initialize SimpleOCRService: {e}")
            self.document_analyzer = None
    
    def extract_text_from_document(self, document: Document) -> str:
        """Extract text from a library document"""
        try:
            file_path = document.file.path
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return ""
            
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.pdf':
                return self._extract_pdf_text(file_path)
            elif file_extension in ['.docx', '.doc']:
                return self._extract_docx_text(file_path)
            elif file_extension == '.txt':
                return self._extract_txt_text(file_path)
            else:
                logger.warning(f"Unsupported file format: {file_extension}")
                return ""
                
        except Exception as e:
            logger.error(f"Error extracting text from document {document.id}: {e}")
            return ""
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file using existing document analyzer"""
        try:
            # First try regular text extraction
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text += page_text + "\n"
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num}: {e}")
                        continue
            
            # If no text extracted, use the document analyzer
            if not text.strip() and self.document_analyzer:
                logger.info(f"Using DocumentAnalyzer for scanned PDF: {file_path}")
                text = self._extract_with_document_analyzer(file_path)
            
            # If still no text, return placeholder
            if not text.strip():
                return f"مستند PDF: {os.path.basename(file_path)}\n(لم يتم استخراج النص الكامل)"
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return f"مستند PDF: {os.path.basename(file_path)}\n(خطأ في استخراج النص)"
    
    def _extract_with_document_analyzer(self, file_path: str) -> str:
        """Extract text using simple OCR service"""
        try:
            if self.document_analyzer and hasattr(self.document_analyzer, 'extract_text_from_pdf'):
                return self.document_analyzer.extract_text_from_pdf(file_path)
            else:
                return ""
        except Exception as e:
            logger.error(f"Error using simple OCR: {e}")
            return ""
    
    def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            return ""
    
    def _extract_txt_text(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read().strip()
        except Exception as e:
            logger.error(f"Error extracting TXT text: {e}")
            return ""
    
    def prepare_library_documents(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """Prepare library documents for RAG indexing"""
        processed_docs = []
        
        for document in documents:
            try:
                # Extract text from document
                text = self.extract_text_from_document(document)
                
                if not text:
                    logger.warning(f"No text extracted from document {document.id}")
                    continue
                
                # Create document metadata
                metadata = {
                    'source': 'library',
                    'document_id': document.id,
                    'title': document.title,
                    'document_type': document.document_type.name if document.document_type else 'Unknown',
                    'uploaded_by': document.uploaded_by.username if document.uploaded_by else 'Unknown',
                    'uploaded_at': document.uploaded_at.isoformat(),
                    'file_path': document.file.name,
                    'description': document.description or ''
                }
                
                # Split text into chunks for better retrieval
                chunks = self._chunk_text(text, chunk_size=500, overlap=50)
                
                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata['chunk_id'] = i
                    chunk_metadata['total_chunks'] = len(chunks)
                    
                    processed_docs.append({
                        'id': f"library_doc_{document.id}_chunk_{i}",
                        'text': chunk,
                        'metadata': chunk_metadata
                    })
                
                logger.info(f"Processed document {document.title}: {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Error processing document {document.id}: {e}")
                continue
        
        return processed_docs
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                sentence_endings = ['.', '؟', '!', '\n']
                for i in range(end, max(start, end - 100), -1):
                    if text[i] in sentence_endings:
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
        
        return chunks
    
    def get_all_library_documents(self) -> List[Document]:
        """Get all public library documents for indexing"""
        return Document.objects.filter(is_public=True).select_related('document_type', 'uploaded_by')
    
    def get_documents_by_type(self, document_type_id: int) -> List[Document]:
        """Get documents by type for indexing"""
        return Document.objects.filter(
            is_public=True,
            document_type_id=document_type_id
        ).select_related('document_type', 'uploaded_by')
