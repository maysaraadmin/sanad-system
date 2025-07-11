from django import template
import os

register = template.Library()

@register.filter
@template.defaultfilters.stringfilter
def is_pdf(value):
    """Check if file is PDF"""
    return value.lower().endswith('.pdf')

@register.filter
@template.defaultfilters.stringfilter
def get_file_extension(value):
    """Get file extension"""
    return os.path.splitext(value)[1].lower()
