from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import Narrator

class NarratorForm(forms.ModelForm):
    class Meta:
        model = Narrator
        fields = [
            'name',
            'birth_year',
            'death_year',
            'biography',
            'reliability',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter narrator name...'),
            }),
            'birth_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Birth year'),
            }),
            'death_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Death year'),
            }),
            'biography': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Enter narrator biography...'),
            }),
            'reliability': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        labels = {
            'name': _('Name'),
            'birth_year': _('Birth Year'),
            'death_year': _('Death Year'),
            'biography': _('Biography'),
            'reliability': _('Reliability'),
        }
        help_texts = {
            'name': _('Enter the full name of the narrator.'),
            'birth_year': _('Enter the birth year of the narrator.'),
            'death_year': _('Enter the death year of the narrator.'),
            'reliability': _("Select the narrator's reliability grade."),
        }

    def clean(self):
        cleaned_data = super().clean()
        birth_year = cleaned_data.get('birth_year')
        death_year = cleaned_data.get('death_year')
        
        if birth_year and death_year and death_year < birth_year:
            raise forms.ValidationError(
                _('Death year cannot be before birth year')
            )
        
        return cleaned_data


class AddTeacherForm(forms.Form):
    """Form for adding teachers to a narrator"""
    existing_teachers = forms.ModelMultipleChoiceField(
        queryset=Narrator.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'dir': 'rtl',
            'data-placeholder': 'اختر الشيوخ الموجودين'
        }),
        required=False,
        label='الشيوخ الموجودون',
        help_text='اختر الشيوخ المسجلين بالفعل في النظام'
    )
    
    new_teacher_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم شيخ جديد',
            'dir': 'rtl'
        }),
        label='إضافة شيخ جديد'
    )
    
    new_teacher_birth_year = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'سنة الميلاد (اختياري)',
            'dir': 'ltr'
        }),
        label='سنة الميلاد'
    )
    
    new_teacher_death_year = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'سنة الوفاة (اختياري)',
            'dir': 'ltr'
        }),
        label='سنة الوفاة'
    )
    
    new_teacher_reliability = forms.ChoiceField(
        choices=[
            ('thiqa', 'ثقة'),
            ('saduq', 'صدوق'),
            ('weak', 'ضعيف'),
            ('unknown', 'مجهول')
        ],
        initial='unknown',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'dir': 'rtl'
        }),
        label='درجة التوثيق'
    )
    
    def __init__(self, narrator_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude the current narrator from the teacher selection
        self.fields['existing_teachers'].queryset = Narrator.objects.exclude(id=narrator_id).order_by('name')
    
    def clean_new_teacher_name(self):
        new_teacher_name = self.cleaned_data.get('new_teacher_name')
        
        # Check if new teacher name already exists
        if new_teacher_name and new_teacher_name.strip():
            if Narrator.objects.filter(name__iexact=new_teacher_name.strip()).exists():
                raise forms.ValidationError(
                    f'الشيخ "{new_teacher_name}" موجود بالفعل في النظام. الرجاء اختياره من القائمة.'
                )
        
        return new_teacher_name
    
    def clean(self):
        cleaned_data = super().clean()
        existing_teachers = cleaned_data.get('existing_teachers', [])
        new_teacher_name = cleaned_data.get('new_teacher_name')
        
        # Check if at least one teacher is selected or created
        if not existing_teachers and not new_teacher_name:
            raise forms.ValidationError(
                'يجب اختيار شيخ موجود على الأقل أو إضافة شيخ جديد'
            )
        
        return cleaned_data
