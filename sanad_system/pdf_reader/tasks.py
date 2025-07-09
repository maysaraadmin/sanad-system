import os
import logging
import fitz  # PyMuPDF
from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from .models import Document

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_pdf_metadata(self, document_id):
    """
    Background task to process PDF metadata.
    
    Args:
        document_id: ID of the Document instance
    """
    try:
        document = Document.objects.get(pk=document_id)
        
        # Check if file exists
        if not document.file:
            logger.warning(f"No file found for document {document_id}")
            return False
            
        file_path = document.file.path if hasattr(document.file, 'path') else None
        
        # For remote storage or if path is not available
        if not file_path or not os.path.exists(file_path):
            # Try to use storage API for remote files
            if default_storage.exists(document.file.name):
                with default_storage.open(document.file.name, 'rb') as f:
                    with fitz.open(stream=f.read(), filetype='pdf') as doc:
                        document.page_count = doc.page_count
                        document.save(update_fields=['page_count'])
                return True
            else:
                logger.error(f"File not found for document {document_id}")
                return False
        
        # Process local file
        with fitz.open(file_path) as doc:
            document.page_count = doc.page_count
            document.save(update_fields=['page_count'])
            
        return True
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} does not exist")
        return False
    except Exception as e:
        logger.error(f"Error processing PDF metadata for document {document_id}: {e}", exc_info=True)
        # Retry the task with exponential backoff
        raise self.retry(exc=e)

@shared_task
def extract_text_from_pdf_task(document_id, max_pages=1000):
    """
    Extract text from a PDF file in the background.
    
    Args:
        document_id: ID of the Document instance
        max_pages: Maximum number of pages to process
        
    Returns:
        str: Extracted text or None if failed
    """
    try:
        document = Document.objects.get(pk=document_id)
        
        if not document.file:
            return None
            
        file_path = document.file.path if hasattr(document.file, 'path') else None
        
        # Handle remote storage
        if not file_path or not os.path.exists(file_path):
            if default_storage.exists(document.file.name):
                with default_storage.open(document.file.name, 'rb') as f:
                    with fitz.open(stream=f.read(), filetype='pdf') as doc:
                        return _extract_text_from_pdf_doc(doc, max_pages)
            return None
            
        # Process local file
        with fitz.open(file_path) as doc:
            return _extract_text_from_pdf_doc(doc, max_pages)
            
    except Exception as e:
        logger.error(f"Error extracting text from PDF {document_id}: {e}", exc_info=True)
        return None

def _extract_text_from_pdf_doc(doc, max_pages):
    """Helper function to extract text from a PyMuPDF document"""
    try:
        text = []
        num_pages = min(len(doc), max_pages)
        
        for page_num in range(num_pages):
            page = doc.load_page(page_num)
            text.append(page.get_text("text"))
            
        return "\n\n".join(text)
    except Exception as e:
        logger.error(f"Error in PDF text extraction: {e}", exc_info=True)
        return None
