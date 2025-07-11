from django.urls import path
from . import views

app_name = 'library_app'

urlpatterns = [
    # Document URLs
    path('', views.DocumentListView.as_view(), name='document_list'),
    path('document/<int:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('document/create/', views.DocumentCreateView.as_view(), name='document_create'),
    path('document/<int:pk>/update/', views.DocumentUpdateView.as_view(), name='document_update'),
    path('document/<int:pk>/delete/', views.DocumentDeleteView.as_view(), name='document_delete'),
    path('document/<int:pk>/view/', views.document_view, name='document_view'),
    path('document/<int:pk>/word-html/', views.word_to_html, name='word_to_html'),
    
    # Document Type URLs
    path('document-type/create/', views.DocumentTypeCreateView.as_view(), name='document_type_create'),
    path('document-type/list/', views.DocumentTypeListView.as_view(), name='document_type_list'),
    
    # AJAX endpoints
    path('document/<int:pk>/toggle-public/', views.toggle_public, name='toggle_public'),
]
