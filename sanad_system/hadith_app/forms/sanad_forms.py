from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import Sanad, SanadNarrator, Narrator

class SanadForm(forms.ModelForm):
    narrators = forms.ModelMultipleChoiceField(
        queryset=Narrator.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'dir': 'rtl',
            'data-placeholder': 'اختر الرواة'
        }),
        required=True,
        help_text=_('اضغط مع الاستمرار على زر Ctrl (أو Command على Mac) لتحديد عدة رواة')
    )
    
    class Meta:
        model = Sanad
        fields = ['chain_order', 'notes', 'narrators']
        widgets = {
            'chain_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'step': 1,
                'dir': 'ltr'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'dir': 'rtl',
                'placeholder': 'ملاحظات إضافية عن السند'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order narrators by name for better UX
        self.fields['narrators'].queryset = Narrator.objects.all().order_by('name')
        
        # If we're editing an existing instance, set initial values
        if self.instance and self.instance.pk:
            self.fields['narrators'].initial = self.instance.narrators.all()
    
    def save(self, commit=True):
        # Save the Sanad instance first without the many-to-many field
        sanad = super().save(commit=False)
        if commit:
            sanad.save()
            
        # Save many-to-many data
        if 'narrators' in self.cleaned_data:
            # Clear existing relations
            sanad.narrators.clear()
            # Add new relations
            for narrator in self.cleaned_data['narrators']:
                SanadNarrator.objects.create(sanad=sanad, narrator=narrator)
                
        return sanad
