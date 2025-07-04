from django import forms
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, CreateView
from django.urls import reverse_lazy

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

class LoginView(FormView):
    template_name = 'hadith_app/login.html'
    form_class = AuthenticationForm
    success_url = reverse_lazy('hadith_app:home')

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        messages.success(self.request, _('تم تسجيل الدخول بنجاح'))
        return super().form_valid(form)

class LogoutView(FormView):
    template_name = 'hadith_app/logout.html'
    success_url = reverse_lazy('hadith_app:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = self.request.GET.get('next', '/')
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, _('تم تسجيل الخروج بنجاح'))
        next_url = request.POST.get('next', self.success_url)
        return redirect(next_url)


class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'hadith_app/register.html'
    success_url = reverse_lazy('hadith_app:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('إنشاء حساب جديد')
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        user = authenticate(username=username, password=password)
        if user:
            login(self.request, user)
            messages.success(self.request, _('تم إنشاء الحساب وتسجيل الدخول بنجاح!'))
        return response
