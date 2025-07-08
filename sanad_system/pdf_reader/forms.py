from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Document

class DocumentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # If user is not staff, hide the is_public field
        if self.user and not self.user.is_staff:
            self.fields['is_public'].widget = forms.HiddenInput()
    
    class Meta:
        model = Document
        fields = ['title', 'description', 'file', 'is_public']
        labels = {
            'title': _('العنوان'),
            'description': _('الوصف'),
            'file': _('الملف'),
            'is_public': _('عام (يمكن للجميع رؤيته)'),
        }
        help_texts = {
            'file': _('يمكنك رفع ملف PDF أو أي مستند نصي آخر'),
            'is_public': _('سيتمكن جميع المستخدمين من رؤية هذا المستند إذا كان عامًا'),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file', False)
        if file:
            # Validate file size (50MB max)
            max_size = 50 * 1024 * 1024  # 50MB
            if file.size > max_size:
                raise forms.ValidationError(_('حجم الملف كبير جدًا. الحد الأقصى المسموح به هو 50 ميجابايت.'))
            
            # Check file extension
            valid_extensions = ['.pdf', '.doc', '.docx', '.txt', '.odt', '.rtf']
            import os
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(_('نوع الملف غير مدعوم. الرجاء تحميل ملف PDF أو نصي.'))
                
        return file
