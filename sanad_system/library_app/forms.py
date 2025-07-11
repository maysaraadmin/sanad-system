from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Document, DocumentType

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'document_type', 'file', 'description', 'is_public']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'العنوان'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'الوصف', 'rows': 3}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'title': _('العنوان'),
            'document_type': _('نوع المستند'),
            'file': _('الملف'),
            'description': _('الوصف'),
            'is_public': _('عام')
        }
        help_texts = {
            'is_public': _('تحديد هذا الخيار سيجعل المستند متاحًا للجميع')
        }

class DocumentTypeForm(forms.ModelForm):
    class Meta:
        model = DocumentType
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نوع المستند'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'الوصف', 'rows': 3})
        }
        labels = {
            'name': _('نوع المستند'),
            'description': _('الوصف')
        }
