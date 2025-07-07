from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Document, DocumentCategory
import os

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'description', 'file', 'category', 'is_public']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter document title')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Enter document description (optional)')
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': _('Document Title'),
            'description': _('Description'),
            'file': _('Document File'),
            'category': _('Category'),
            'is_public': _('Make this document public'),
        }
        help_texts = {
            'is_public': _('Check this if you want this document to be visible to all users'),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show categories the user has permission to use
        self.fields['category'].queryset = DocumentCategory.objects.all()
        
        # Set initial uploaded_by to current user
        if self.user and not self.instance.pk:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            self.fields['uploaded_by'] = forms.ModelChoiceField(
                queryset=User.objects.filter(pk=self.user.pk),
                widget=forms.HiddenInput(),
                initial=self.user.pk
            )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if not file:
            raise ValidationError(_('الرجاء اختيار ملف للرفع'))
            
        # Limit file size (412MB)
        max_size = 412 * 1024 * 1024  # 412MB
        if file.size > max_size:
            size_mb = file.size / (1024 * 1024)
            raise ValidationError(
                _('حجم الملف كبير جداً. الحجم الأقصى المسموح به هو 412 ميجابايت. حجم الملف المحدد: %.2f ميجابايت') % size_mb
            )
        
        # Check file extension
        ext = os.path.splitext(file.name)[1].lower()
        valid_extensions = ['.pdf', '.doc', '.docx']
        if ext not in valid_extensions:
            raise ValidationError(_('نوع الملف غير مدعوم. يرجى رفع ملف من الأنواع التالية: %s') % ', '.join(valid_extensions))
        
        # Clean the filename
        filename = os.path.basename(file.name)
        # Remove any potentially dangerous characters
        import re
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        file.name = filename
            
        return file
        
    def clean(self):
        cleaned_data = super().clean()
        # Add any cross-field validation here if needed
        return cleaned_data

class DocumentCategoryForm(forms.ModelForm):
    class Meta:
        model = DocumentCategory
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
