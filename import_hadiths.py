#!/usr/bin/env python
"""
Simple script to import hadith books from JSON files
Usage:
    python import_hadiths.py --book nawawi40    # Import specific book
    python import_hadiths.py --path books-json/by_book/forties  # Import all books in directory
    python import_hadiths.py --book bukhari --limit 10  # Import 10 hadiths for testing
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sanad_system.settings')
sys.path.append(os.path.join(os.path.dirname(__file__), 'sanad_system'))
django.setup()

from django.core.management import execute_from_command_line

def main():
    # Pass arguments to Django management command
    argv = [
        'manage.py',
        'import_hadith_books',
    ] + sys.argv[1:]
    
    execute_from_command_line(argv)

if __name__ == '__main__':
    main()
