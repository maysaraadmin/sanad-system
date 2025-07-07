from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from ..models import Sanad, Hadith, SanadNarrator
from ..forms.sanad_forms import SanadForm

class SanadCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Sanad
    form_class = SanadForm
    template_name = 'hadith_app/sanad_form.html'
    success_message = _("تمت إضافة السند بنجاح")
    
    def get_success_url(self):
        return reverse_lazy('hadith_app:hadith_detail', kwargs={'pk': self.kwargs['hadith_id']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('إضافة سند جديد')
        context['action'] = _('إضافة')
        context['hadith'] = Hadith.objects.get(pk=self.kwargs['hadith_id'])
        return context
    
    def form_valid(self, form):
        form.instance.hadith_id = self.kwargs['hadith_id']
        form.instance.added_by = self.request.user
        return super().form_valid(form)
