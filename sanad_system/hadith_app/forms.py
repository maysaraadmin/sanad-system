from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm, PasswordChangeForm as AuthPasswordChangeForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from django.conf import settings
import os

from .models import UserProfile, Narrator, Hadith, Sanad, SanadNarrator, HadithCategory

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'البريد الإلكتروني'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'الاسم الأول'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم العائلة'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'اسم المستخدم'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'كلمة المرور'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'تأكيد كلمة المرور'
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم المستخدم أو البريد الإلكتروني',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'كلمة المرور'
        })
    )


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('الاسم الأول'),
            'dir': 'rtl'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('اسم العائلة'),
            'dir': 'rtl'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('البريد الإلكتروني'),
            'dir': 'ltr',
            'type': 'email'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'email', 'bio', 'location', 'phone_number', 'birth_date', 'website', 'twitter', 'facebook']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('نبذة شخصية عنك'),
                'rows': 4,
                'dir': 'rtl'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('المدينة، الدولة'),
                'dir': 'rtl'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('+9665XXXXXXXX'),
                'dir': 'ltr',
                'type': 'tel'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'dir': 'ltr'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': _('https://example.com'),
                'dir': 'ltr'
            }),
            'twitter': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('اسم المستخدم بدون @'),
                'dir': 'ltr'
            }),
            'facebook': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': _('https://facebook.com/username'),
                'dir': 'ltr'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
        return profile


class AvatarUploadForm(forms.ModelForm):
    avatar = forms.ImageField(
        required=False,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif'],
                message=_('الصيغ المدعومة: JPG, JPEG, PNG, GIF')
            )
        ],
        widget=forms.FileInput(attrs={
            'class': 'd-none',
            'accept': 'image/*',
            'id': 'avatar-upload',
            'onchange': 'previewAvatar(this)'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ('avatar',)
    
    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Limit file size to 2MB
            if avatar.size > 2 * 1024 * 1024:
                raise forms.ValidationError(_('حجم الملف يجب أن لا يتجاوز 2 ميجابايت'))
            # Validate file type by content, not just extension
            try:
                from PIL import Image
                Image.open(avatar).verify()
            except:
                raise forms.ValidationError(_('الملف المرفوع ليس صورة صالحة'))
        return avatar


class CustomPasswordChangeForm(AuthPasswordChangeForm):
    old_password = forms.CharField(
        label=_('كلمة المرور الحالية'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'class': 'form-control',
            'placeholder': _('أدخل كلمة المرور الحالية'),
            'dir': 'ltr'
        }),
    )
    
    new_password1 = forms.CharField(
        label=_('كلمة المرور الجديدة'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'form-control',
            'placeholder': _('أدخل كلمة المرور الجديدة'),
            'dir': 'ltr'
        }),
    )
    
    new_password2 = forms.CharField(
        label=_('تأكيد كلمة المرور الجديدة'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'form-control',
            'placeholder': _('أعد إدخال كلمة المرور الجديدة'),
            'dir': 'ltr'
        }),
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].help_text = _(
            'يجب أن تحتوي كلمة المرور على 8 أحرف على الأقل وتشمل أرقامًا وحروفًا ورموزًا خاصة.'
        )


class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'كلمة المرور الحالية'
        }),
        label='كلمة المرور الحالية'
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'كلمة المرور الجديدة'
        }),
        label='كلمة المرور الجديدة'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'تأكيد كلمة المرور الجديدة'
        }),
        label='تأكيد كلمة المرور الجديدة'
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError('كلمة المرور الحالية غير صحيحة.')
        return old_password

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError('كلمتا المرور الجديدتان غير متطابقتان.')
        return cleaned_data

    def save(self):
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        self.user.save()
        return self.user


class HadithForm(forms.ModelForm):
    narrator_chain = forms.CharField(
        label='سند الحديث',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'أدخل سلسلة الرواة مفصولة بفواصل',
            'rows': 3,
            'dir': 'rtl',
            'required': True
        })
    )
    
    class Meta:
        model = Hadith
        fields = ['text', 'source', 'source_page', 'source_hadith_number', 'grade', 'categories']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'نص الحديث',
                'rows': 5,
                'dir': 'rtl',
                'required': True
            }),
            'source': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مصدر الحديث',
                'dir': 'rtl',
                'required': True
            }),
            'source_page': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الصفحة',
                'dir': 'rtl',
                'required': False
            }),
            'source_hadith_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الحديث في المصدر',
                'dir': 'rtl',
                'required': False
            }),
            'grade': forms.Select(attrs={
                'class': 'form-select',
                'dir': 'rtl',
                'required': True
            }),
            'categories': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'dir': 'rtl',
                'required': False
            })
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['categories'].queryset = HadithCategory.objects.all()
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
    def save(self, commit=True):
        hadith = super().save(commit=False)
        if self.user:
            hadith.added_by = self.user
        if commit:
            hadith.save()
        return hadith

class NarratorForm(forms.ModelForm):
    class Meta:
        model = Narrator
        fields = ['name', 'biography', 'reliability']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الراوي',
                'dir': 'rtl'
            }),
            'biography': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'نبذة عن الراوي',
                'rows': 3,
                'dir': 'rtl'
            }),
            'reliability': forms.Select(attrs={
                'class': 'form-control'
            })
        }
