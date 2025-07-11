from django.urls import path
from .views import (
    DocumentListView,
    DocumentDetailView,
    DocumentCreateView,
    DocumentUpdateView,
    DocumentDeleteView,
    DocumentTypeCreateView,
    DocumentTypeListView,
    toggle_public
)

app_name = 'library_app'

urlpatterns = [
    # Document URLs
    path('', DocumentListView.as_view(), name='document_list'),
    path('document/<int:pk>/', DocumentDetailView.as_view(), name='document_detail'),
    path('document/create/', DocumentCreateView.as_view(), name='document_create'),
    path('document/<int:pk>/update/', DocumentUpdateView.as_view(), name='document_update'),
    path('document/<int:pk>/delete/', DocumentDeleteView.as_view(), name='document_delete'),
    
    # Document Type URLs
    path('types/', DocumentTypeListView.as_view(), name='document_type_list'),
    path('types/create/', DocumentTypeCreateView.as_view(), name='document_type_create'),
    
    # AJAX endpoints
    path('document/<int:pk>/toggle-public/', toggle_public, name='toggle_public'),
]
