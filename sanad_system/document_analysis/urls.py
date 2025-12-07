# document_analysis/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('analyses/', views.DocumentAnalysisListCreateView.as_view(), name='document-analysis-list'),
    path('analyses/<int:pk>/', views.DocumentAnalysisDetailView.as_view(), name='document-analysis-detail'),
    path('dashboard/', views.document_analysis_dashboard, name='document-analysis-dashboard'),
]