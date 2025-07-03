from django import forms
from django.utils.translation import gettext_lazy as _
from hadith_app.models import Hadith, Sanad, SanadNarrator

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
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': _('Add any additional notes...'),
            }),
        }
        labels = {
            'text': _('Hadith Text'),
            'source': _('Source Book'),
            'source_page': _('Page Number'),
            'source_hadith_number': _('Hadith Number'),
            'grade': _('Grade'),
        }
        help_texts = {
            'text': _('Enter the complete hadith text.'),
            'source': _('Enter the name of the source book.'),
            'source_page': _('Enter the page number where this hadith appears.'),
            'source_hadith_number': _('Enter the hadith number in the source book.'),
            'grade': _('Select the authenticity grade of this hadith.'),
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
