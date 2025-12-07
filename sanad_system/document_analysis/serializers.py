# document_analysis/serializers.py
from rest_framework import serializers
from .models import DocumentAnalysis

class DocumentAnalysisSerializer(serializers.ModelSerializer):
    document_name = serializers.SerializerMethodField()
    document_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentAnalysis
        fields = [
            'id', 'document', 'library_document', 'document_name', 'document_url', 
            'status', 'result', 'error_message', 'created_at', 
            'updated_at', 'user'
        ]
        read_only_fields = ['user', 'status', 'result', 'error_message', 'created_at', 'updated_at']
        extra_kwargs = {
            'document': {'required': False},
            'library_document': {'required': False}
        }
    
    def get_document_name(self, obj):
        return obj.get_document_name()
    
    def get_document_url(self, obj):
        url = obj.get_document_url()
        return url if url else None
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)