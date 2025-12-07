# document_analysis/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from .models import DocumentAnalysis
from .serializers import DocumentAnalysisSerializer
from .tasks import process_document_analysis

class DocumentAnalysisListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentAnalysisSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        # Staff can see all analyses, regular users see only their own
        if self.request.user.is_staff:
            return DocumentAnalysis.objects.all().order_by('-created_at')
        else:
            return DocumentAnalysis.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Ensure a file is provided
        if 'document' not in self.request.FILES:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"document": "لم يتم إرسال أي ملف."})
        
        instance = serializer.save(user=self.request.user, document=self.request.FILES['document'])
        
        # Process document immediately (synchronous)
        process_document_analysis(instance.id)

class DocumentAnalysisDetailView(generics.RetrieveAPIView):
    queryset = DocumentAnalysis.objects.all()
    serializer_class = DocumentAnalysisSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

@login_required
def document_analysis_dashboard(request):
    """Dashboard view for document analysis"""
    # Show all analyses if user is staff, otherwise show only user's analyses
    if request.user.is_staff:
        analyses = DocumentAnalysis.objects.all().order_by('-created_at')
    else:
        analyses = DocumentAnalysis.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'document_analysis/dashboard.html', {
        'analyses': analyses, 
        'active_page': 'document_analysis',
        'show_all_users': request.user.is_staff
    })