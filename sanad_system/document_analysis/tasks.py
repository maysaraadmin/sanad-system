# document_analysis/tasks.py
import os
import logging
from celery import shared_task
from django.conf import settings
from .models import DocumentAnalysis
from .document_analyzer import DocumentAnalyzer

logger = logging.getLogger(__name__)

# Global analyzer instance to prevent reinitialization
_analyzer_instance = None

def get_analyzer():
    """Get or create the global analyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = DocumentAnalyzer()
        logger.info("Created new DocumentAnalyzer instance")
    else:
        logger.info("Reusing existing DocumentAnalyzer instance")
    return _analyzer_instance

def process_document_analysis(analysis_id):
    """
    Process document analysis with progress tracking
    """
    try:
        analysis = DocumentAnalysis.objects.get(id=analysis_id)
        analysis.status = 'processing'
        analysis.save()
        
        # Get analyzer instance (singleton)
        analyzer = get_analyzer()
        
        # Get the file path
        if analysis.library_document:
            # Use library document file
            file_path = analysis.library_document.file.path
        elif analysis.document:
            # Use uploaded document file
            file_path = analysis.document.path
        else:
            raise ValueError("No document file available for analysis")
        
        # Process the document
        result = analyzer.analyze_document(file_path)
        
        # Save results
        analysis.result = result
        analysis.status = 'completed'
        analysis.save()
        
        return str(analysis_id)
        
    except Exception as e:
        logger.error(f"Error processing document analysis {analysis_id}: {str(e)}")
        analysis.status = 'failed'
        analysis.error_message = str(e)
        analysis.save()
        raise