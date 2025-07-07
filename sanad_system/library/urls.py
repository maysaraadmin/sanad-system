from django.urls import path, include
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_GET
from rest_framework.routers import DefaultRouter
from . import views
from .api_views import DocumentSuggestionsAPIView, document_search_api

app_name = 'library'

# API URLs
api_patterns = [
    path('suggestions/', DocumentSuggestionsAPIView.as_view(), name='api_document_suggestions'),
    path('search/', document_search_api, name='api_document_search'),
]

urlpatterns = [
    path('', views.DocumentListView.as_view(), name='document_list'),
    path('upload/', login_required(views.DocumentCreateView.as_view()), name='document_upload'),
    path('document/<int:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('document/<int:pk>/page/<int:page>/', views.PDFPageView.as_view(), name='document_page'),
    path('document/<int:pk>/download/', views.document_download, name='document_download'),
    path('document/<int:pk>/delete/', login_required(views.DocumentDeleteView.as_view()), name='document_delete'),
    path('document/<int:pk>/extract-hadiths/', 
         login_required(require_http_methods(['POST'])(views.extract_hadiths)), 
         name='extract_hadiths'),
    path('category/<int:category_id>/', views.DocumentCategoryView.as_view(), name='document_category'),
    path('search/', views.DocumentSearchView.as_view(), name='document_search'),
    path('extraction-progress/<str:task_id>/', 
         login_required(views.check_extraction_progress), 
         name='check_extraction_progress'),
    
    # API endpoints
    path('api/library/', include((api_patterns, 'library_api'), namespace='library_api')),
]
