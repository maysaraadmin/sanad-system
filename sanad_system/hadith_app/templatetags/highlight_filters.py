from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter(name='highlight')
def highlight(text, search_term):
    if not search_term or not text:
        return text
    
    # Escape special regex characters in the search term
    escaped_search = re.escape(search_term)
    
    # Create a case-insensitive regex pattern
    pattern = re.compile(f'({escaped_search})', re.IGNORECASE)
    
    # Replace matches with highlighted spans
    highlighted = pattern.sub(
        lambda match: f'<span class="highlight">{match.group(1)}</span>',
        str(text)
    )
    
    return mark_safe(highlighted)
