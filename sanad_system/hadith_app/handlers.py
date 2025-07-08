from django.shortcuts import render

def handler404(request, exception=None, template_name='404.html'):
    """Custom 404 error handler."""
    return render(request, template_name, status=404)

def handler500(request, template_name='500.html'):
    """Custom 500 error handler."""
    return render(request, template_name, status=500)
