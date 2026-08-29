from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from hadith_app.models import Hadith
from rag_app.services import RAGService
from rag_app.models import RAGConfiguration
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Index hadiths for RAG system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hadith-ids',
            nargs='+',
            type=int,
            help='Specific hadith IDs to index (optional)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of hadiths to index (for testing)',
        )
        parser.add_argument(
            '--reindex',
            action='store_true',
            help='Clear existing data and re-index',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for processing (default: 100)',
        )
    
    def handle(self, *args, **options):
        try:
            # Initialize RAG service
            rag_service = RAGService()
            
            # Handle reindexing
            if options['reindex']:
                self.stdout.write('Clearing existing RAG data...')
                from rag_app.services import ChromaDBService
                from rag_app.models import DocumentEmbedding
                
                # Clear ChromaDB safely
                chroma_service = ChromaDBService()
                if chroma_service.collection:
                    chroma_service.clear_collection()
                chroma_service._initialize_client()
                
                # Clear Django embeddings
                DocumentEmbedding.objects.all().delete()
                
                self.stdout.write(self.style.SUCCESS('Existing data cleared.'))
            
            # Get hadiths to index
            hadith_ids = options.get('hadith_ids')
            limit = options.get('limit')
            batch_size = options.get('batch_size')
            
            if hadith_ids:
                hadiths = Hadith.objects.filter(id__in=hadith_ids)
                self.stdout.write(f'Indexing {len(hadith_ids)} specific hadiths...')
            elif limit:
                hadiths = Hadith.objects.all()[:limit]
                self.stdout.write(f'Indexing first {limit} hadiths...')
            else:
                hadiths = Hadith.objects.all()
                total_count = hadiths.count()
                self.stdout.write(f'Indexing all {total_count} hadiths...')
            
            # Process in batches
            total_processed = 0
            for i in range(0, hadiths.count(), batch_size):
                batch = hadiths[i:i + batch_size]
                batch_ids = list(batch.values_list('id', flat=True))
                
                try:
                    rag_service.index_hadiths(batch_ids)
                    total_processed += len(batch)
                    
                    progress = (total_processed / hadiths.count()) * 100
                    self.stdout.write(
                        f'Processed {total_processed}/{hadiths.count()} hadiths ({progress:.1f}%)'
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing batch {i//batch_size + 1}: {e}')
                    )
                    continue
            
            # Final statistics
            from rag_app.services import ChromaDBService
            chroma_service = ChromaDBService()
            total_documents = chroma_service.get_document_count()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Indexing completed! Total documents indexed: {total_documents}'
                )
            )
            
        except Exception as e:
            logger.error(f"Error in index_hadiths command: {e}")
            raise CommandError(f'Indexing failed: {e}')
