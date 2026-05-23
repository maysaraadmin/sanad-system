from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Document, DocumentType
import os

# File upload constants
MAX_FILE_SIZE = 52428800  # 50MB in bytes
ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif']
ALLOWED_EXTENSIONS_DISPLAY = ', '.join(ALLOWED_EXTENSIONS)

# Map extension → list of valid leading magic-byte sequences
_MAGIC_BYTES = {
    '.pdf':  [b'%PDF'],
    '.docx': [b'PK\x03\x04'],
    '.doc':  [b'\xd0\xcf\x11\xe0'],
    '.txt':  None,           # Plain text — any bytes allowed
    '.jpg':  [b'\xff\xd8\xff'],
    '.jpeg': [b'\xff\xd8\xff'],
    '.png':  [b'\x89PNG'],
    '.gif':  [b'GIF87a', b'GIF89a'],
}


class DocumentForm(forms.ModelForm):
    def clean_file(self):
        file = self.cleaned_data.get('file', False)
        if file:
            # Check file is not empty
            if file.size == 0:
                raise forms.ValidationError(_('لا يمكن رفع ملف فارغ'))

            # Check file size
            if file.size > MAX_FILE_SIZE:
                raise forms.ValidationError(
                    _('حجم الملف كبير جداً. الحد الأقصى هو 50 ميجابايت.')
                )

            # Check declared file extension
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise forms.ValidationError(
                    _('نوع الملف غير مسموح به. أنواع الملفات المسموح بها: %s') %
                    ALLOWED_EXTENSIONS_DISPLAY
                )

            # Verify actual file content against magic bytes (prevents extension spoofing)
            allowed_signatures = _MAGIC_BYTES.get(ext)
            if allowed_signatures is not None:
                header = file.read(8)
                file.seek(0)
                if not any(header.startswith(sig) for sig in allowed_signatures):
                    raise forms.ValidationError(
                        _('محتوى الملف لا يتطابق مع امتداده. يرجى رفع ملف صحيح.')
                    )

        return file

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
            'is_public': _('تحديد هذا الخيار سيجعل المستند متاحًا للجميع'),
            'file': _(
                'الحد الأقصى للحجم: 50 ميجابايت. أنواع الملفات المسموح بها: %s' % 
                ALLOWED_EXTENSIONS_DISPLAY
            )
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
