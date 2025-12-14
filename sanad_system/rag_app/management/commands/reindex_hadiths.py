from django.core.management.base import BaseCommand
from rag_app.services import RAGService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Re-index all hadiths in ChromaDB with complete text structure'

    def handle(self, *args, **options):
        """Execute the re-indexing command"""
        self.stdout.write('Starting re-indexing of all hadiths...')
        
        try:
            # Initialize RAG service
            rag_service = RAGService()
            
            # Re-index all hadiths
            rag_service.reindex_all_hadiths()
            
            self.stdout.write(
                self.style.SUCCESS('Successfully re-indexed all hadiths in ChromaDB')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during re-indexing: {str(e)}')
            )
            logger.error(f"Re-indexing failed: {e}")
