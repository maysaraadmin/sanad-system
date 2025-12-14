import sys
import io
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from hadith_app.models import Hadith, HadithBook, HadithCategory, HadithText, Sanad, SanadNarrator, SanadText

# Set UTF-8 encoding for stdout
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

class Command(BaseCommand):
    help = 'Delete all hadiths and related data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompting'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        confirm = options['confirm']
        dry_run = options['dry_run']
        
        # Get current counts
        hadith_count = Hadith.objects.count()
        hadith_text_count = HadithText.objects.count()
        sanad_count = Sanad.objects.count()
        sanad_narrator_count = SanadNarrator.objects.count()
        sanad_text_count = SanadText.objects.count()
        book_count = HadithBook.objects.count()
        category_count = HadithCategory.objects.count()
        
        if hadith_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No hadiths found in the database.')
            )
            return
        
        # Show what will be deleted
        self.stdout.write(
            self.style.WARNING('The following data will be deleted:')
        )
        self.stdout.write(f'  Hadiths: {hadith_count}')
        self.stdout.write(f'  Hadith Texts: {hadith_text_count}')
        self.stdout.write(f'  Sanads: {sanad_count}')
        self.stdout.write(f'  Sanad Narrators: {sanad_narrator_count}')
        self.stdout.write(f'  Sanad Texts: {sanad_text_count}')
        self.stdout.write(f'  Hadith Books: {book_count}')
        self.stdout.write(f'  Hadith Categories: {category_count}')
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('Dry run completed. No data was deleted.')
            )
            return
        
        # Confirm deletion
        if not confirm:
            response = input('\nAre you sure you want to delete all hadiths and related data? (yes/no): ')
            if response.lower() != 'yes':
                self.stdout.write('Operation cancelled.')
                return
        
        try:
            with transaction.atomic():
                # Delete in order to respect foreign key constraints
                self.stdout.write('Deleting hadith texts...')
                HadithText.objects.all().delete()
                
                self.stdout.write('Deleting sanad narrators...')
                SanadNarrator.objects.all().delete()
                
                self.stdout.write('Deleting sanad texts...')
                SanadText.objects.all().delete()
                
                self.stdout.write('Deleting sanads...')
                Sanad.objects.all().delete()
                
                self.stdout.write('Deleting hadiths...')
                Hadith.objects.all().delete()
                
                self.stdout.write('Deleting hadith books...')
                HadithBook.objects.all().delete()
                
                self.stdout.write('Deleting hadith categories...')
                HadithCategory.objects.all().delete()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nSuccessfully deleted all hadiths and related data:\n'
                        f'  - {hadith_count} hadiths\n'
                        f'  - {hadith_text_count} hadith texts\n'
                        f'  - {sanad_count} sanads\n'
                        f'  - {sanad_narrator_count} sanad narrators\n'
                        f'  - {sanad_text_count} sanad texts\n'
                        f'  - {book_count} books\n'
                        f'  - {category_count} categories'
                    )
                )
                
        except Exception as e:
            raise CommandError(f'Error deleting hadiths: {e}')
