from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_GET
import os
import re
from library_app.models import Document, DocumentType

# Import document processing libraries
def check_pypdf2():
    try:
        import PyPDF2
        return True
    except ImportError:
        return False

def check_docx():
    try:
        import docx
        return True
    except ImportError:
        return False

class DocumentSearchView(TemplateView):
    template_name = 'library_app/document_search.html'

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        document_type = request.GET.get('type', '')
        page = request.GET.get('page', 1)
        
        results = []
        if query:
            results = self.search_documents(query, document_type)
        
        # Paginate results
        paginator = Paginator(results, 10)
        page_obj = paginator.get_page(page)
        
        context = {
            'query': query,
            'results': page_obj,
            'document_types': DocumentType.objects.all(),
            'selected_type': document_type,
            'pypdf2_available': check_pypdf2(),
            'docx_available': check_docx(),
        }
        
        return self.render_to_response(context)

    def search_documents(self, query, document_type_filter=''):
        """Search inside document contents"""
        results = []
        documents = Document.objects.all()
        
        if document_type_filter:
            documents = documents.filter(document_type__id=document_type_filter)
        
        for document in documents:
            if not document.file_exists:
                continue
                
            content_matches = self.extract_and_search(document.file.path, query)
            
            if content_matches:
                results.append({
                    'document': document,
                    'matches': content_matches,
                    'match_count': len(content_matches)
                })
        
        # Sort by match count (most relevant first)
        results.sort(key=lambda x: x['match_count'], reverse=True)
        return results

    def extract_and_search(self, file_path, query):
        """Extract text from document and search for query"""
        matches = []
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.pdf' and check_pypdf2():
                matches = self.search_pdf(file_path, query)
            elif file_ext in ['.doc', '.docx'] and check_docx():
                matches = self.search_docx(file_path, query)
            elif file_ext == '.txt':
                matches = self.search_text(file_path, query)
        except Exception as e:
            print(f"Error searching {file_path}: {e}")
        
        return matches

    def search_pdf(self, file_path, query):
        """Search inside PDF file"""
        matches = []
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    page_matches = self.find_text_matches(text, query)
                    if page_matches:
                        matches.extend([{
                            'page': page_num,
                            'text': match,
                            'context': self.get_context(text, match)
                        } for match in page_matches])
        except Exception as e:
            print(f"PDF search error: {e}")
        
        return matches

    def search_docx(self, file_path, query):
        """Search inside Word document"""
        matches = []
        try:
            import docx
            doc = docx.Document(file_path)
            for para_num, paragraph in enumerate(doc.paragraphs, 1):
                if paragraph.text.strip():
                    para_matches = self.find_text_matches(paragraph.text, query)
                    if para_matches:
                        matches.extend([{
                            'paragraph': para_num,
                            'text': match,
                            'context': self.get_context(paragraph.text, match)
                        } for match in para_matches])
        except Exception as e:
            print(f"DOCX search error: {e}")
        
        return matches

    def search_text(self, file_path, query):
        """Search inside text file"""
        matches = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                line_matches = self.find_text_matches(content, query)
                if line_matches:
                    matches = [{
                        'line': i + 1,
                        'text': match,
                        'context': self.get_context(content, match)
                    } for i, match in enumerate(line_matches)]
        except Exception as e:
            print(f"Text search error: {e}")
        
        return matches

    def find_text_matches(self, text, query):
        """Find all occurrences of query in text"""
        matches = []
        # Case-insensitive search
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        for match in pattern.finditer(text):
            matches.append(match.group())
        return matches

    def get_context(self, text, match, context_chars=100):
        """Get context around a match"""
        match_pos = text.lower().find(match.lower())
        if match_pos == -1:
            return match
        
        start = max(0, match_pos - context_chars)
        end = min(len(text), match_pos + len(match) + context_chars)
        
        context = text[start:end]
        if start > 0:
            context = '...' + context
        if end < len(text):
            context = context + '...'
        
        # Highlight the match
        highlighted = context.replace(match, f"<mark>{match}</mark>")
        return highlighted

@require_GET
def document_search_api(request):
    """AJAX API for document search"""
    query = request.GET.get('q', '')
    document_type = request.GET.get('type', '')
    
    if not query:
        return JsonResponse({'results': []})
    
    search_view = DocumentSearchView()
    results = search_view.search_documents(query, document_type)
    
    # Format results for JSON response
    formatted_results = []
    for result in results:
        formatted_results.append({
            'id': result['document'].id,
            'title': result['document'].title,
            'document_type': result['document'].document_type.name,
            'match_count': result['match_count'],
            'matches': result['matches'][:5],  # Limit to first 5 matches
            'url': result['document'].get_absolute_url()
        })
    
    return JsonResponse({'results': formatted_results})
