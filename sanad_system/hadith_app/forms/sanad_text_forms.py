"""
Sanad Text Forms

This module provides forms for managing sanad texts (specific text versions
for each sanad of a hadith).
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from hadith_app.models import SanadText


class SanadTextForm(forms.ModelForm):
    """
    Form for creating and editing sanad texts
    """
    class Meta:
        model = SanadText
        fields = ['text', 'source_reference', 'variation_notes', 'is_primary']
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'أدخل نص الحديث كما رواه هذا السند...'
            }),
            'source_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: صحيح البخاري، كتاب الإيمان، حديث رقم 2'
            }),
            'variation_notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'أي اختلافات في النص مقارنة بالنسخ الأخرى...'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'text': _('نص الحديث'),
            'source_reference': _('المصدر المحدد'),
            'variation_notes': _('ملاحظات الاختلاف'),
            'is_primary': _('النص الأساسي')
        }
        help_texts = {
            'text': _('أدخل نص الحديث كما رواه هذا السند تحديداً'),
            'source_reference': _('المصدر المحدد لهذه الرواية إذا كان مختلفاً عن المصدر الرئيسي'),
            'variation_notes': _('أي اختلافات في الألفاظ أو المعنى مقارنة بالنسخ الأخرى'),
            'is_primary': _('حدد هذا كالنص الأساسي للحديث إذا كان هو الأكثر شيوعاً')
        }
    
    def clean_text(self):
        """Validate the text field"""
        text = self.cleaned_data.get('text')
        if not text or not text.strip():
            raise forms.ValidationError(_('نص الحديث مطلوب'))
        return text.strip()
    
    def __init__(self, *args, **kwargs):
        hadith = kwargs.pop('hadith', None)
        super().__init__(*args, **kwargs)
        
        # If editing existing text, show hadith context
        if hadith:
            self.hadith = hadith
        
        # Add form-control class to all fields
        for field_name, field in self.fields.items():
            if field_name != 'is_primary':
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'


class SanadTextCreateForm(SanadTextForm):
    """
    Form specifically for creating new sanad texts
    """
    def __init__(self, *args, **kwargs):
        sanad = kwargs.pop('sanad', None)
        super().__init__(*args, **kwargs)
        
        if sanad:
            self.instance.sanad = sanad
            # Pre-populate with hadith text if available
            if not self.instance.text and sanad.hadith.text:
                self.initial['text'] = sanad.hadith.text
                self.initial['variation_notes'] = _('نسخة من النص الأساسي للحديث')
