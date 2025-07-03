from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import UserProfile

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'avatar',
            'bio',
            'theme',
        ]
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Tell us about yourself...'),
            }),
            'theme': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        labels = {
            'avatar': _('Profile Picture'),
            'bio': _('Biography'),
            'theme': _('Theme'),
        }
        help_texts = {
            'avatar': _('Upload a profile picture (max 5MB)'),
            'bio': _('Write a short description about yourself.'),
            'theme': _('Choose your preferred theme.'),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if avatar.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError(
                    _('Profile picture must be less than 5MB')
                )
        return avatar

class AvatarUploadForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }
        labels = {
            'avatar': _('Profile Picture'),
        }
        help_texts = {
            'avatar': _('Upload a profile picture (max 5MB)'),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if avatar.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError(
                    _('Profile picture must be less than 5MB')
                )
        return avatar
