from django.shortcuts import render

def custom_404_view(request, exception=None):
    """Custom 404 error handler."""
    return render(request, '404.html', status=404)

def custom_500_view(request):
    """Custom 500 error handler."""
    return render(request, '500.html', status=500)
