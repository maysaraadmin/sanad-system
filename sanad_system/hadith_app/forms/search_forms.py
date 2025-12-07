from django import forms
from django.utils.translation import gettext_lazy as _

class SearchForm(forms.Form):
    q = forms.CharField(
        label=_('Search'),
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search hadiths and narrators...'),
            'aria-label': _('Search'),
        })
    )
    
    search_in = forms.ChoiceField(
        label=_('Search In'),
        choices=[
            ('all', _('All Content')),
            ('hadith', _('Hadiths Only')),
            ('narrator', _('Narrators Only')),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    grade_filter = forms.MultipleChoiceField(
        label=_('Filter by Grade'),
        choices=[
            ('sahih', _('صحيح (Sahih)')),
            ('hasan', _('حسن (Hasan)')),
            ('daif', _('ضعيف (Daif)')),
            ('mawdu', _('موضوع (Mawdu)')),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        })
    )
    
    show_sanad = forms.BooleanField(
        label=_('Show Sanad Chain'),
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )
    
    def clean_q(self):
        q = self.cleaned_data.get('q', '').strip()
        if len(q) < 3:
            raise forms.ValidationError(
                _('Search query must be at least 3 characters long')
            )
        return q
