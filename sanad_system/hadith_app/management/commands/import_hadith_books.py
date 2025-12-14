import sys
import io
from django.core.management.base import BaseCommand
from django.db import transaction
import json
import os
from hadith_app.models import Hadith, HadithBook, HadithCategory

# Set UTF-8 encoding for stdout
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

class Command(BaseCommand):
    help = 'Import hadith books from JSON files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            default='books-json/by_book',
            help='Path to the books JSON directory'
        )
        parser.add_argument(
            '--book',
            type=str,
            help='Import specific book (e.g., nawawi40, bukhari, muslim)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force import even if books already exist'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of hadiths to import (for testing)'
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check what books are already imported'
        )

    def handle(self, *args, **options):
        base_path = options['path']
        specific_book = options['book']
        force = options['force']
        limit = options['limit']
        check = options['check']
        
        # If check flag is used, show current import status
        if check:
            self.check_import_status()
            return
        
        # Get the project base directory
        from django.conf import settings
        project_base = settings.BASE_DIR.parent
        full_path = os.path.join(project_base, base_path)
        
        if not os.path.exists(full_path):
            self.stdout.write(
                self.style.ERROR(f'Directory not found: {full_path}')
            )
            return

        # Find JSON files
        json_files = []
        if specific_book:
            # Find specific book
            for root, dirs, files in os.walk(full_path):
                for file in files:
                    if file == f'{specific_book}.json':
                        json_files.append(os.path.join(root, file))
        else:
            # Find all JSON files
            for root, dirs, files in os.walk(full_path):
                for file in files:
                    if file.endswith('.json'):
                        json_files.append(os.path.join(root, file))
        
        if not json_files:
            self.stdout.write(
                self.style.ERROR('No JSON files found')
            )
            return
        
        self.stdout.write(f'Found {len(json_files)} JSON file(s) to import')
        
        total_imported = 0
        total_skipped = 0
        
        for json_file in json_files:
            self.stdout.write(f'\nProcessing: {json_file}')
            try:
                imported, skipped = self.import_book(json_file, force, limit)
                total_imported += imported
                total_skipped += skipped
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error importing {json_file}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nImport completed!\n'
                f'Total hadiths imported: {total_imported}\n'
                f'Total hadiths skipped: {total_skipped}'
            )
        )

    def import_book(self, json_file, force=False, limit=None):
        # Try different encodings to handle Arabic text properly
        encodings = ['utf-8', 'utf-8-sig', 'cp1256', 'iso-8859-6']
        data = None
        
        for encoding in encodings:
            try:
                with open(json_file, 'r', encoding=encoding) as f:
                    data = json.load(f)
                self.stdout.write(f'Successfully opened file with {encoding} encoding')
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.stdout.write(f'Error with {encoding}: {e}')
                continue
        
        if data is None:
            raise Exception(f'Could not read file {json_file} with any supported encoding')
        
        # Extract book information
        metadata = data['metadata']
        book_title = metadata['arabic']['title']
        book_author = metadata['arabic']['author']
        
        # Check if book already exists
        existing_book = HadithBook.objects.filter(title=book_title).first()
        if existing_book and not force:
            self.stdout.write(
                self.style.WARNING(f'Book "{book_title}" already exists. Use --force to reimport.')
            )
            return 0, 0
        
        if existing_book and force:
            self.stdout.write(f'Deleting existing book "{book_title}" and its hadiths...')
            Hadith.objects.filter(source__contains=book_title).delete()
            existing_book.delete()
        
        with transaction.atomic():
            # Create the book
            book = HadithBook.objects.create(
                title=book_title,
                author=book_author,
                description=metadata['arabic'].get('introduction', '')[:500]  # Limit description length
            )
            
            self.stdout.write(f'Created book: {book.title}')
            
            # Create or get category
            category_name = self.get_category_name(book_title)
            category, created = HadithCategory.objects.get_or_create(
                name=category_name,
                defaults={'description': f'أحاديث من كتاب {book_title}'}
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')
            
            # Import hadiths
            imported_count = 0
            skipped_count = 0
            
            hadiths_to_import = data['hadiths']
            if limit:
                hadiths_to_import = hadiths_to_import[:limit]
            
            for hadith_data in hadiths_to_import:
                try:
                    hadith = self.create_hadith(hadith_data, book, category)
                    imported_count += 1
                    
                    if imported_count % 100 == 0:
                        self.stdout.write(f'  Imported {imported_count} hadiths...')
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  Skipped hadith {hadith_data.get("idInBook", "unknown")}: {e}')
                    )
                    skipped_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'  Completed: {imported_count} imported, {skipped_count} skipped'
                )
            )
            
            return imported_count, skipped_count

    def create_hadith(self, hadith_data, book, category):
        arabic_text = hadith_data['arabic']
        
        # Extract main hadith text (between quotes if present)
        hadith_text = arabic_text
        if '"' in arabic_text:
            start = arabic_text.find('"')
            end = arabic_text.rfind('"')
            if start != -1 and end != -1 and end > start:
                hadith_text = arabic_text[start+1:end]
        
        # Determine grade based on book type
        grade = self.determine_grade(book.title, hadith_data)
        
        # Create hadith
        hadith = Hadith.objects.create(
            text=hadith_text,
            source=f"{book.title} - حديث رقم {hadith_data['idInBook']}",
            source_hadith_number=str(hadith_data['idInBook']),
            grade=grade,
            context=arabic_text if arabic_text != hadith_text else None
        )
        
        # Add to category
        hadith.categories.add(category)
        
        return hadith

    def determine_grade(self, book_title, hadith_data):
        """Determine hadith grade based on book type"""
        if 'صحيح' in book_title.lower() or 'bukhari' in book_title.lower() or 'muslim' in book_title.lower():
            return 'sahih'
        elif 'سنن' in book_title.lower() or 'abudawud' in book_title.lower() or 'tirmidhi' in book_title.lower() or 'nasai' in book_title.lower() or 'ibnmajah' in book_title.lower():
            return 'hasan'  # Most hadiths in these books are hasan
        elif 'موطأ' in book_title.lower() or 'malik' in book_title.lower():
            return 'hasan'
        elif 'أربعون' in book_title.lower() or '40' in book_title.lower() or 'نووي' in book_title.lower():
            return 'sahih'  # Forty hadith collections are usually sahih
        else:
            return 'hasan'  # Default grade

    def get_category_name(self, book_title):
        """Generate appropriate category name based on book title"""
        if 'صحيح البخاري' in book_title or 'bukhari' in book_title.lower():
            return 'صحيح البخاري'
        elif 'صحيح مسلم' in book_title or 'muslim' in book_title.lower():
            return 'صحيح مسلم'
        elif 'سنن أبي داود' in book_title or 'abudawud' in book_title.lower():
            return 'سنن أبي داود'
        elif 'سنن الترمذي' in book_title or 'tirmidhi' in book_title.lower():
            return 'سنن الترمذي'
        elif 'سنن النسائي' in book_title or 'nasai' in book_title.lower():
            return 'سنن النسائي'
        elif 'سنن ابن ماجه' in book_title or 'ibnmajah' in book_title.lower():
            return 'سنن ابن ماجه'
        elif 'موطأ مالك' in book_title or 'malik' in book_title.lower():
            return 'موطأ مالك'
        elif 'مسند أحمد' in book_title or 'ahmed' in book_title.lower():
            return 'مسند أحمد'
        elif 'سنن الدارمي' in book_title or 'darimi' in book_title.lower():
            return 'سنن الدارمي'
        elif 'أربعون' in book_title or '40' in book_title:
            return 'الأربعون النووية'
        else:
            return book_title[:50]  # Truncate if too long
