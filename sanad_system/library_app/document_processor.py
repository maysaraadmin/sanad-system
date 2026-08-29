import re
import logging
import PyPDF2
import docx
from pathlib import Path
from django.conf import settings
from hadith_app.models import Hadith, Narrator

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    text = []
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text.append(page.extract_text())
        return '\n\n'.join(text)
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(file_path)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        return ""

def extract_hadiths(text):
    """Extract potential hadiths from text"""
    # Common hadith starter patterns in Arabic
    patterns = [
        r'(?:حدثنا|أخبرنا|أنبأنا|سمعت|قال|عن|قال رسول الله|قال النبي|عن النبي)[^.]*?[.،]',
        r'قَالَ رَسُولُ اللَّهِ.*?[.،]',
        r'عَنْ.*?عَنِ النَّبِيِّ.*?[.،]',
    ]
    
    hadiths = []
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            hadiths.append({
                'text': match.group(0).strip(),
                'start': match.start(),
                'end': match.end()
            })
    return hadiths

def extract_narrators(text):
    """Extract potential narrator names from text"""
    # Common narrator name patterns in Arabic
    patterns = [
        r'[\u0600-\u06FF\s]{3,}بن[\u0600-\u06FF\s]{3,}',  # Names with 'bin'
        r'[\u0600-\u06FF]{2,}\s+[\u0600-\u06FF]{2,}',  # Two or more Arabic words
    ]
    
    narrators = []
    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            name = match.group(0).strip()
            # Basic validation to skip common non-names
            if len(name) < 3 or any(word in name for word in ['الله', 'رسول', 'النبي', 'قال', 'عن']):
                continue
            narrators.append({
                'name': name,
                'start': match.start(),
                'end': match.end()
            })
    return narrators

def compare_with_existing(hadiths, narrators):
    """Compare extracted data with existing database"""
    results = {
        'hadith_matches': [],
        'narrator_matches': [],
        'new_hadiths': [],
        'new_narrators': []
    }
    
    # Check hadiths
    for hadith in hadiths:
        # Simple text search for now - could be enhanced with more sophisticated matching
        matches = Hadith.objects.filter(text__icontains=hadith['text'][:100])  # First 100 chars for matching
        if matches.exists():
            results['hadith_matches'].extend(list(matches))
        else:
            results['new_hadiths'].append(hadith)
    
    # Check narrators
    for narrator in narrators:
        matches = Narrator.objects.filter(name__icontains=narrator['name'])
        if matches.exists():
            results['narrator_matches'].extend(list(matches))
        else:
            results['new_narrators'].append(narrator)
    
    return results

def process_document(document):
    """Process a document and extract hadith/narrator information"""
    import os
    from django.conf import settings
    
    debug_info = {
        'file_path': document.file.path if hasattr(document, 'file') and hasattr(document.file, 'path') else 'No file path',
        'file_exists': os.path.exists(document.file.path) if hasattr(document, 'file') and hasattr(document.file, 'path') else False,
        'file_size': os.path.getsize(document.file.path) if hasattr(document, 'file') and hasattr(document.file, 'path') and os.path.exists(document.file.path) else 0,
        'steps': {}
    }
    
    try:
        # Verify file exists and is accessible
        if not debug_info['file_exists']:
            return {
                'error': f'File not found at: {debug_info["file_path"]}',
                'debug': debug_info
            }
        
        # Extract text based on file type
        debug_info['steps']['file_type'] = 'Checking file type'
        file_path = document.file.path
        text = ""
        
        if file_path.lower().endswith('.pdf'):
            debug_info['steps']['extraction'] = 'Extracting text from PDF'
            text = extract_text_from_pdf(file_path)
        elif file_path.lower().endswith(('.docx', '.doc')):
            debug_info['steps']['extraction'] = 'Extracting text from DOCX'
            text = extract_text_from_docx(file_path)
        else:
            return {
                'error': f'Unsupported file format: {os.path.splitext(file_path)[1]}',
                'debug': debug_info
            }
        
        debug_info['steps']['text_extraction'] = {
            'success': bool(text),
            'text_length': len(text) if text else 0,
            'sample': text[:200] + '...' if text else ''
        }
        
        if not text or not text.strip():
            return {
                'error': 'Extracted text is empty',
                'debug': debug_info
            }
        
        # Extract hadiths and narrators
        debug_info['steps']['extraction'] = 'Extracting hadiths and narrators'
        hadiths = extract_hadiths(text)
        narrators = extract_narrators(text)
        
        debug_info['steps']['extraction_results'] = {
            'hadiths_found': len(hadiths),
            'narrators_found': len(narrators),
            'hadith_sample': hadiths[0] if hadiths else None,
            'narrator_sample': narrators[0] if narrators else None
        }
        
        # Compare with existing data
        debug_info['steps']['comparison'] = 'Comparing with existing data'
        comparison_results = compare_with_existing(hadiths, narrators)
        
        result = {
            'document': document,
            'text': text[:5000] + '...' if len(text) > 5000 else text,  # Limit text size
            'extracted_hadiths': hadiths[:100],  # Limit number of hadiths
            'extracted_narrators': narrators[:100],  # Limit number of narrators
            'comparison': comparison_results,
            'stats': {
                'total_hadiths': len(hadiths),
                'total_narrators': len(narrators),
                'matched_hadiths': len(comparison_results.get('hadith_matches', [])),
                'matched_narrators': len(comparison_results.get('narrator_matches', [])),
                'new_hadiths': len(comparison_results.get('new_hadiths', [])),
                'new_narrators': len(comparison_results.get('new_narrators', []))
            },
            'debug': debug_info
        }
        
        return result
        
    except Exception as e:
        import traceback
        debug_info['error'] = str(e)
        debug_info['traceback'] = traceback.format_exc()
        return {
            'error': f'Error processing document: {str(e)}',
            'debug': debug_info
        }
