from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django.urls import reverse_lazy

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

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, _('تم تسجيل الخروج بنجاح'))
        return redirect(self.success_url)
