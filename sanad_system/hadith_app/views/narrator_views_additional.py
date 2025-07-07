from django.views.generic import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from ..models import Narrator
from ..forms import NarratorForm

class NarratorCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Narrator
    form_class = NarratorForm
    template_name = 'hadith_app/narrator_form.html'
    success_url = reverse_lazy('hadith_app:narrator_list')
    success_message = _("تمت إضافة الراوي بنجاح")
    
    def form_valid(self, form):
        form.instance.added_by = self.request.user
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('إضافة راوي جديد')
        context['action'] = _('إضافة')
        return context

class NarratorUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Narrator
    form_class = NarratorForm
    template_name = 'hadith_app/narrator_form.html'
    success_url = reverse_lazy('hadith_app:narrator_list')
    success_message = _("تم تحديث بيانات الراوي بنجاح")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('تعديل بيانات الراوي')
        context['action'] = _('حفظ التغييرات')
        return context

class NarratorDeleteView(LoginRequiredMixin, DeleteView):
    model = Narrator
    template_name = 'hadith_app/narrator_confirm_delete.html'
    success_url = reverse_lazy('hadith_app:narrator_list')
    success_message = _("تم حذف الراوي بنجاح")
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)
