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
