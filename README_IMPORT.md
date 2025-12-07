# Hadith Import Guide

This guide shows you how to import hadith collections from your JSON files into the Sanad system.

## Available Books

### Forties Collections
- `nawawi40` - الأربعون النووية (Nawawi's 40 Hadith)
- `qudsi40` - الأربعون القدسية (40 Qudsi Hadith)
- `shahwaliullah40` - الأربعون الشاه ولي الله (Shah Waliullah's 40)

### Major Hadith Books
- `bukhari` - صحيح البخاري (Sahih Bukhari) - ~7,000 hadiths
- `muslim` - صحيح مسلم (Sahih Muslim) - ~5,000 hadiths
- `abudawud` - سنن أبي داود (Sunan Abu Dawud) - ~4,000 hadiths
- `tirmidhi` - سنن الترمذي (Sunan Tirmidhi) - ~3,000 hadiths
- `nasai` - سنن النسائي (Sunan an-Nasa'i) - ~4,000 hadiths
- `ibnmajah` - سنن ابن ماجه (Sunan Ibn Majah) - ~3,000 hadiths
- `malik` - موطأ مالك (Muwatta Malik) - ~1,500 hadiths
- `ahmed` - مسند أحمد (Musnad Ahmad) - ~2,000 hadiths
- `darimi` - سنن الدارمي (Sunan ad-Darimi) - ~1,000 hadiths

## Import Commands

### 1. Import a Specific Book

```bash
# Import Nawawi 40 hadiths
python manage.py import_hadith_books --book nawawi40

# Import Sahih Bukhari
python manage.py import_hadith_books --book bukhari

# Import a specific book with limit (for testing)
python manage.py import_hadith_books --book bukhari --limit 10
```

### 2. Import All Books in a Directory

```bash
# Import all forties collections
python manage.py import_hadith_books --path books-json/by_book/forties

# Import all major hadith books
python manage.py import_hadith_books --path books-json/by_book/the_9_books

# Import all books (entire collection)
python manage.py import_hadith_books --path books-json/by_book
```

### 3. Force Re-import

If you want to re-import books that already exist:

```bash
python manage.py import_hadith_books --book nawawi40 --force
```

### 4. Using the Simple Script

You can also use the provided script:

```bash
# Import Nawawi 40
python import_hadiths.py --book nawawi40

# Import with limit for testing
python import_hadiths.py --book bukhari --limit 5
```

## Features

- **Automatic categorization**: Books are automatically categorized
- **Grade assignment**: Hadith grades are assigned based on book type
- **Text extraction**: Main hadith text is extracted from full Arabic text
- **Context preservation**: Full chain of narration is stored in context field
- **Error handling**: Skips problematic hadiths and reports issues
- **Progress tracking**: Shows import progress every 100 hadiths

## Recommendations

### For Testing
Start with smaller collections first:

```bash
python manage.py import_hadith_books --book nawawi40
python manage.py import_hadith_books --book qudsi40
python manage.py import_hadith_books --book shahwaliullah40
```

### For Production
Import major books one by one to monitor performance:

```bash
python manage.py import_hadith_books --book bukhari
python manage.py import_hadith_books --book muslim
python manage.py import_hadith_books --book abudawud
# ... continue with other books
```

## Database Impact

- Each hadith creates 1 record in the `Hadith` table
- Each book creates 1 record in the `HadithBook` table
- Categories are created automatically
- Total expected records: ~30,000+ hadiths across all books

## Troubleshooting

### Memory Issues
For large books like Bukhari, you might need to increase memory or import in smaller batches using `--limit`.

### Encoding Issues
The import script handles UTF-8 encoding automatically for Arabic text.

### Duplicate Imports
Use `--force` flag to re-import books that already exist in the database.
