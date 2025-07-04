from django.conf import settings
from django.utils.translation import get_language

def menu_items(request):
    return {
        'active_page': request.resolver_match.url_name if hasattr(request, 'resolver_match') else ''
    }
    
def theme(request):
    """
    Adds theme and RTL support to the template context.
    """
    # Get current language
    language = get_language()
    
    # Check if the current language is RTL (Arabic, Hebrew, etc.)
    is_rtl = language in {'ar', 'he', 'fa', 'ur'}
    
    # Get theme from session or use default
    theme = request.session.get('theme', 'light')
    
    return {
        'theme': theme,
        'is_rtl': is_rtl,
        'current_language': language,
        'LANGUAGES': settings.LANGUAGES,
    }