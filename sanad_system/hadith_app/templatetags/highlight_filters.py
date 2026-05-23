from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
import re

register = template.Library()

@register.filter(name='highlight')
def highlight(text, search_term):
    if not search_term or not text:
        return text

    # Escape the source text to prevent stored XSS before injecting any HTML
    escaped_text = escape(str(text))

    # Escape special regex characters in the search term
    escaped_search = re.escape(escape(str(search_term)))

    # Create a case-insensitive regex pattern
    pattern = re.compile(f'({escaped_search})', re.IGNORECASE)

    # Replace matches with highlighted spans (text is already HTML-escaped)
    highlighted = pattern.sub(
        lambda match: f'<span class="highlight">{match.group(1)}</span>',
        escaped_text
    )

    return mark_safe(highlighted)
