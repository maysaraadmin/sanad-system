from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.vary import vary_on_cookie
from django.views.generic import RedirectView
from . import views

app_name = 'pdf_reader'

# API Router
router = DefaultRouter()
# Future API endpoints can be registered here

# Common URL patterns for document management
document_patterns = [
    # List and create documents
    path('', 
        login_required(views.DocumentListView.as_view()),
        name='document_list'
    ),
    path('upload/', 
        login_required(views.DocumentCreateView.as_view()),
        name='document_upload'
    ),
    
    # Document detail and actions
    path('<int:pk>/', 
        login_required(views.DocumentDetailView.as_view()),
        name='document_detail'
    ),
    path('<int:pk>/edit/', 
        login_required(views.DocumentUpdateView.as_view()),
        name='document_update'
    ),
    path('<int:pk>/delete/', 
        login_required(views.DocumentDeleteView.as_view()),
        name='document_delete'
    ),
    path('<int:pk>/view/', 
        vary_on_cookie(login_required(views.pdf_viewer)),
        name='document_view'
    ),
    path('<int:pk>/download/', 
        never_cache(login_required(views.serve_document)),
        name='document_download'
    ),
    
    # PDF viewer with specific page
    path('<int:pk>/view/page/<int:page>/', 
        vary_on_cookie(login_required(views.pdf_viewer)),
        name='document_view_page'
    ),
    
    # Document actions
    path('<int:pk>/toggle-public/', 
        login_required(views.toggle_public_status),
        name='document_toggle_public'
    ),
    
    # API endpoints for document actions
    path('api/v1/document/<int:pk>/metadata/', 
        login_required(views.get_pdf_metadata),
        name='api_document_metadata'
    ),
]

# API v1 endpoints
api_v1_patterns = [
    path('upload/', 
        require_http_methods(['POST'])(views.upload_pdf), 
        name='upload_pdf'
    ),
    path('metadata/', 
        require_http_methods(['GET'])(views.get_pdf_metadata), 
        name='get_pdf_metadata'
    ),
]

# Legacy endpoints (deprecated, will be removed in future)
legacy_patterns = [
    path('legacy/upload/', 
        views.upload_pdf, 
        name='upload_pdf_legacy'
    ),
    path('legacy/metadata/', 
        views.get_pdf_metadata, 
        name='get_pdf_metadata_legacy'
    ),
    path('legacy/pdf/<path:file_path>', 
        views.serve_pdf, 
        name='serve_pdf_legacy'
    ),
]

# Main URL patterns
urlpatterns = [
    # Document management
    path('', include(document_patterns)),
    
    # API v1
    path('api/v1/', include(api_v1_patterns)),
    
    # Legacy endpoints
    path('legacy/', include(legacy_patterns)),
    
    # Redirect old URLs to new ones
    path('view/<int:pk>/', 
        RedirectView.as_view(pattern_name='pdf_reader:document_view', permanent=True),
        name='old_document_view_redirect'
    ),
]
