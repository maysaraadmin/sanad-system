from django import forms
from django.utils.translation import gettext_lazy as _
from hadith_app.models import Hadith, Sanad, SanadNarrator, HadithCategory, HadithText

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
        fields = ['narrator', 'order', 'narration_method']
        widgets = {
            'narrator': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'narration_method': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'طريقة الرواية (مثال: حدثنا، أخبرنا، أنبأنا)',
                'dir': 'rtl'
            }),
        }
        labels = {
            'narrator': _('الراوي'),
            'order': _('الترتيب في السند'),
            'narration_method': _('طريقة الرواية'),
        }
        help_texts = {
            'order': 'مكان الراوي في سلسلة السند (1 للأول، 2 للثاني، وهكذا)',
            'narration_method': 'كيفية رواية هذا الراوي عن شيخه'
        }


class HadithTextForm(forms.ModelForm):
    """Form for adding multiple text versions to a hadith"""
    class Meta:
        model = HadithText
        fields = ['text', 'source_reference', 'narrator_chain', 'variation_notes']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'أدخل نص الحديث هنا...',
                'rows': 6,
                'dir': 'rtl'
            }),
            'source_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'المصدر المحدد (مثال: صحيح البخاري، كتاب الإيمان)',
                'dir': 'rtl'
            }),
            'narrator_chain': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'سلسلة الرواة لهذه الرواية...',
                'rows': 3,
                'dir': 'rtl'
            }),
            'variation_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'ملاحظات حول الاختلافات في هذه الرواية...',
                'rows': 3,
                'dir': 'rtl'
            })
        }
        labels = {
            'text': 'نص الحديث',
            'source_reference': 'المصدر المحدد',
            'narrator_chain': 'سلسلة الرواة',
            'variation_notes': 'ملاحظات الاختلاف'
        }
        help_texts = {
            'text': 'أدخل نص الحديث كما ورد في المصدر المحدد',
            'source_reference': 'حدد المصدر الدقيق لهذه الرواية',
            'narrator_chain': 'ادخل سلسلة الرواة لهذه الرواية المحددة',
            'variation_notes': 'أي ملاحظات حول الاختلافات بين هذه الرواية والروايات الأخرى'
        }


class AddHadithTextForm(forms.Form):
    """Form for adding a new text version to an existing hadith"""
    text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'أدخل نص الحديث الجديد هنا...',
            'rows': 6,
            'dir': 'rtl',
            'required': True
        }),
        label='نص الحديث',
        required=True,
        help_text='أدخل النص الجديد للحديث'
    )
    
    source_reference = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'المصدر المحدد (اختياري)',
            'dir': 'rtl'
        }),
        label='المصدر المحدد',
        help_text='حدد المصدر الدقيق لهذه الرواية'
    )
    
    narrator_chain = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'سلسلة الرواة (اختياري)...',
            'rows': 3,
            'dir': 'rtl'
        }),
        label='سلسلة الرواة',
        help_text='ادخل سلسلة الرواة لهذه الرواية المحددة'
    )
    
    variation_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'ملاحظات الاختلاف (اختياري)...',
            'rows': 3,
            'dir': 'rtl'
        }),
        label='ملاحظات الاختلاف',
        help_text='أي ملاحظات حول الاختلافات بين هذه الرواية والروايات الأخرى'
    )
    
    make_primary = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='جعل هذا النص هو النص الأساسي',
        help_text='سيحل هذا النص محل النص الأساسي الحالي'
    )
