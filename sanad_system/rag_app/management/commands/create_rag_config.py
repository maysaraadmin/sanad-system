from django.core.management.base import BaseCommand, CommandError
from rag_app.models import RAGConfiguration
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create default RAG configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            default='Default Configuration',
            help='Configuration name',
        )
        parser.add_argument(
            '--embedding-model',
            type=str,
            default='aubmindlab/arabert-base',
            help='Embedding model name',
        )
        parser.add_argument(
            '--llm-model',
            type=str,
            default='arabic-llm',
            help='LLM model name',
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=500,
            help='Text chunk size',
        )
        parser.add_argument(
            '--chunk-overlap',
            type=int,
            default=50,
            help='Text chunk overlap',
        )
        parser.add_argument(
            '--max-context',
            type=int,
            default=5,
            help='Maximum context items',
        )
        parser.add_argument(
            '--similarity-threshold',
            type=float,
            default=0.7,
            help='Similarity threshold',
        )
        parser.add_argument(
            '--activate',
            action='store_true',
            help='Activate this configuration',
        )
    
    def handle(self, *args, **options):
        try:
            # Check if configuration already exists
            existing_config = RAGConfiguration.objects.filter(
                name=options['name']
            ).first()
            
            if existing_config:
                self.stdout.write(
                    self.style.WARNING(f'Configuration "{options["name"]}" already exists.')
                )
                if not self.confirm_overwrite():
                    self.stdout.write('Operation cancelled.')
                    return
            
            # Create or update configuration
            config_data = {
                'name': options['name'],
                'embedding_model': options['embedding_model'],
                'llm_model': options['llm_model'],
                'chunk_size': options['chunk_size'],
                'chunk_overlap': options['chunk_overlap'],
                'max_context': options['max_context'],
                'similarity_threshold': options['similarity_threshold'],
                'is_active': options['activate'],
            }
            
            if existing_config:
                for key, value in config_data.items():
                    setattr(existing_config, key, value)
                existing_config.save()
                config = existing_config
                self.stdout.write(
                    self.style.SUCCESS(f'Configuration "{options["name"]}" updated.')
                )
            else:
                config = RAGConfiguration.objects.create(**config_data)
                self.stdout.write(
                    self.style.SUCCESS(f'Configuration "{options["name"]}" created.')
                )
            
            # If activating, deactivate others
            if options['activate']:
                RAGConfiguration.objects.exclude(pk=config.pk).update(is_active=False)
                self.stdout.write(
                    self.style.SUCCESS(f'Configuration "{options["name"]}" is now active.')
                )
            
            # Display configuration details
            self.stdout.write('\nConfiguration Details:')
            self.stdout.write(f'  Name: {config.name}')
            self.stdout.write(f'  Embedding Model: {config.embedding_model}')
            self.stdout.write(f'  LLM Model: {config.llm_model}')
            self.stdout.write(f'  Chunk Size: {config.chunk_size}')
            self.stdout.write(f'  Chunk Overlap: {config.chunk_overlap}')
            self.stdout.write(f'  Max Context: {config.max_context}')
            self.stdout.write(f'  Similarity Threshold: {config.similarity_threshold}')
            self.stdout.write(f'  Active: {config.is_active}')
            
        except Exception as e:
            logger.error(f"Error in create_rag_config command: {e}")
            raise CommandError(f'Configuration creation failed: {e}')
    
    def confirm_overwrite(self):
        """Ask user for confirmation to overwrite"""
        try:
            response = input('Do you want to overwrite the existing configuration? [y/N]: ')
            return response.lower().startswith('y')
        except (KeyboardInterrupt, EOFError):
            return False
