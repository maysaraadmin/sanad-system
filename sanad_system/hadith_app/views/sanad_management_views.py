"""
Sanad Management Views

This module provides views for managing sanads (chains of narrators),
including creating, editing, and deleting sanads for hadiths.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from hadith_app.models import Hadith, Sanad, SanadNarrator
from hadith_app.forms import SanadForm


class SanadUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for editing an existing sanad"""
    model = Sanad
    form_class = SanadForm
    template_name = 'hadith_app/sanad_edit.html'
    
    def get_success_url(self):
        return reverse_lazy('hadith_app:hadith_detail', kwargs={'pk': self.object.hadith.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hadith'] = self.object.hadith
        context['current_narrators'] = self.object.sanadnarrator_set.all().order_by('order')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('تم تحديث السند بنجاح'))
        return super().form_valid(form)


class SanadDeleteView(LoginRequiredMixin, DeleteView):
    """Delete view for removing a sanad"""
    model = Sanad
    template_name = 'hadith_app/sanad_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('hadith_app:hadith_detail', kwargs={'pk': self.object.hadith.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hadith'] = self.object.hadith
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('تم حذف السند بنجاح'))
        return super().delete(request, *args, **kwargs)


@require_GET
def sanad_list_view(request, hadith_id):
    """
    Display all sanads for a hadith with management options
    """
    hadith = get_object_or_404(Hadith, id=hadith_id)
    sanads = hadith.asanid.all().prefetch_related('sanadnarrator_set__narrator')
    
    context = {
        'hadith': hadith,
        'sanads': sanads
    }
    
    return render(request, 'hadith_app/sanad_list.html', context)


@login_required
@require_POST
def sanad_duplicate_view(request, sanad_id):
    """
    Duplicate an existing sanad with all its narrators
    """
    sanad = get_object_or_404(Sanad, id=sanad_id)
    
    # Create new sanad
    new_sanad = Sanad.objects.create(
        hadith=sanad.hadith,
        is_mutawatir=sanad.is_mutawatir,
        notes=f"نسخة من: {sanad.notes if sanad.notes else 'بدون ملاحظات'}"
    )
    
    # Copy all narrators
    for sanad_narrator in sanad.sanadnarrator_set.all():
        SanadNarrator.objects.create(
            sanad=new_sanad,
            narrator=sanad_narrator.narrator,
            order=sanad_narrator.order,
            narration_method=sanad_narrator.narration_method
        )
    
    messages.success(request, _('تم نسخ السند بنجاح'))
    return redirect('hadith_app:hadith_detail', pk=sanad.hadith.id)


@login_required
@require_POST
def sanad_clear_narrators_view(request, sanad_id):
    """
    Remove all narrators from a sanad (keep sanad, clear narrators)
    """
    sanad = get_object_or_404(Sanad, id=sanad_id)
    
    # Delete all narrator relationships
    sanad.sanadnarrator_set.all().delete()
    
    messages.success(request, _('تم إزالة جميع الرواة من السند بنجاح'))
    return redirect('hadith_app:sanad_narrators', sanad_id=sanad.id)
