from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
import os

register = template.Library()

@register.simple_tag(takes_context=True)
def pdf_reader(context, filename):
    """
    Renders the PDF reader component with the given PDF filename or URL.
    If filename is a full URL, it will be used directly.
    Otherwise, it's treated as a relative path in MEDIA_ROOT.
    Usage: {% pdf_reader document.file.url %}
    """
    # If it's already a URL, use it directly
    if filename.startswith(('http://', 'https://', '/')):
        pdf_url = filename
    else:
        # Otherwise, construct the URL using the media URL pattern
        from django.conf import settings
        from urllib.parse import quote
        
        # Clean the filename and ensure it's URL-encoded
        filename = os.path.basename(filename)
        encoded_filename = quote(filename)
        
        # Build the full URL
        pdf_url = f'/media/documents/{encoded_filename}'
    
    # Log for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"PDF Reader loading URL: {pdf_url}")
    
    return mark_safe(render_to_string('pdf_reader/pdf_reader_component.html', {
        'pdf_url': pdf_url,  # This will be used by the JavaScript
        'pdf_filename': os.path.basename(filename),  # Just the filename for display
        'request': context.get('request')
    }))
