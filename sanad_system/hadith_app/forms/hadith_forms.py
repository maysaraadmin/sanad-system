from django import forms
from django.utils.translation import gettext_lazy as _
from hadith_app.models import Hadith, Sanad, SanadNarrator, HadithCategory

class HadithForm(forms.ModelForm):
    sanad_text = forms.CharField(
        label=_('Sanad Text'),
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': _('Enter the sanad chain text here...'),
            'class': 'form-control',
        }),
        help_text=_('Enter the sanad chain text. Each narrator should be separated by a newline.')
    )

    class Meta:
        model = Hadith
        fields = [
            'text',
            'source',
            'source_page',
            'source_hadith_number',
            'grade',
            'categories',
            'context',
            'reference_page',
            'reference_edition',
        ]
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 6,
                'class': 'form-control',
                'placeholder': _('Enter the hadith text here...'),
            }),
            'source': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter the source book...'),
            }),
            'source_page': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter the page number...'),
            }),
            'source_hadith_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter the hadith number...'),
            }),
            'grade': forms.Select(attrs={
                'class': 'form-select',
            }),
            'categories': forms.SelectMultiple(attrs={
                'class': 'form-select',
            }),
            'context': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter the context...'),
            }),
            'reference_page': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter reference page...'),
            }),
            'reference_edition': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter reference edition...'),
            }),
        }
        labels = {
            'text': _('نص الحديث'),
            'source': _('المصدر'),
            'source_page': _('رقم الصفحة'),
            'source_hadith_number': _('رقم الحديث'),
            'grade': _('الدرجة'),
            'categories': _('التصنيفات'),
            'context': _('السياق'),
            'reference_page': _('صفحة المرجع'),
            'reference_edition': _('طبعة المرجع'),
        }
        help_texts = {
            'text': _('أدخل نص الحديث كاملاً.'),
            'source': _('أدخل اسم المصدر.'),
            'source_page': _('أدخل رقم الصفحة التي يظهر فيها الحديث.'),
            'source_hadith_number': _('أدخل رقم الحديث في المصدر.'),
            'grade': _('اختر درجة صحة الحديث.'),
            'categories': _('اختر التصنيفات المناسبة للحديث.'),
            'context': _('أدخل سياق الحديث إن وجد.'),
            'reference_page': _('أدخل رقم صفحة المرجع.'),
            'reference_edition': _('أدلت طبعة المرجع.'),
        }

class SanadNarratorForm(forms.ModelForm):
    class Meta:
        model = SanadNarrator
        fields = ['narrator', 'order']
        widgets = {
            'narrator': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'narrator': _('Narrator'),
            'order': _('Position in Chain'),
        }
