"""
Sanad Text Views

This module provides views for managing sanad texts (specific text versions
for each sanad of a hadith).
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.http import JsonResponse
from hadith_app.models import Hadith, Sanad, SanadText
from hadith_app.forms.sanad_text_forms import SanadTextForm, SanadTextCreateForm


@require_GET
def sanad_text_detail_view(request, sanad_id):
    """
    Display the text for a specific sanad
    """
    sanad = get_object_or_404(Sanad, id=sanad_id)
    
    # Try to get the sanad text, or create one if it doesn't exist
    sanad_text, created = SanadText.objects.get_or_create(
        sanad=sanad,
        defaults={'text': sanad.hadith.text}
    )
    
    # Get all sanad texts for this hadith for comparison
    all_sanad_texts = SanadText.objects.filter(
        sanad__hadith=sanad.hadith
    ).select_related('sanad').order_by('-is_primary', 'sanad__id')
    
    context = {
        'sanad': sanad,
        'hadith': sanad.hadith,
        'sanad_text': sanad_text,
        'all_sanad_texts': all_sanad_texts,
        'created': created
    }
    
    return render(request, 'hadith_app/sanad_text_detail.html', context)


class SanadTextCreateView(CreateView):
    """
    Create a new sanad text
    """
    model = SanadText
    form_class = SanadTextCreateForm
    template_name = 'hadith_app/sanad_text_create.html'
    
    def get_success_url(self):
        return reverse_lazy('hadith_app:sanad_text_detail', kwargs={'sanad_id': self.object.sanad.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sanad = get_object_or_404(Sanad, id=self.kwargs['sanad_id'])
        context['sanad'] = sanad
        context['hadith'] = sanad.hadith
        return context
    
    def form_valid(self, form):
        sanad = get_object_or_404(Sanad, id=self.kwargs['sanad_id'])
        form.instance.sanad = sanad
        messages.success(self.request, _('تم إنشاء نص السند بنجاح'))
        return super().form_valid(form)


class SanadTextUpdateView(UpdateView):
    """
    Update an existing sanad text
    """
    model = SanadText
    form_class = SanadTextForm
    template_name = 'hadith_app/sanad_text_edit.html'
    
    def get_success_url(self):
        return reverse_lazy('hadith_app:sanad_text_detail', kwargs={'sanad_id': self.object.sanad.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sanad'] = self.object.sanad
        context['hadith'] = self.object.sanad.hadith
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('تم تحديث نص السند بنجاح'))
        return super().form_valid(form)


@require_POST
def set_primary_sanad_text_view(request, sanad_text_id):
    """
    Set a sanad text as the primary text for the hadith
    """
    sanad_text = get_object_or_404(SanadText, id=sanad_text_id)
    
    # Set this as primary and unset others
    SanadText.objects.filter(
        sanad__hadith=sanad_text.sanad.hadith
    ).update(is_primary=False)
    sanad_text.is_primary = True
    sanad_text.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': _('تم تعيين النص كأساسي بنجاح')
        })
    
    messages.success(request, _('تم تعيين النص كأساسي بنجاح'))
    return redirect('hadith_app:sanad_text_detail', sanad_id=sanad_text.sanad.id)


@require_GET
def hadith_sanad_texts_view(request, hadith_id):
    """
    Display all sanad texts for a hadith
    """
    hadith = get_object_or_404(Hadith, id=hadith_id)
    
    sanad_texts = SanadText.objects.filter(
        sanad__hadith=hadith
    ).select_related('sanad').order_by('-is_primary', 'sanad__id')
    
    # Check which sanads don't have texts yet
    sanads_without_texts = Sanad.objects.filter(
        hadith=hadith
    ).exclude(
        id__in=sanad_texts.values_list('sanad_id', flat=True)
    )
    
    context = {
        'hadith': hadith,
        'sanad_texts': sanad_texts,
        'sanads_without_texts': sanads_without_texts
    }
    
    return render(request, 'hadith_app/hadith_sanad_texts.html', context)


@require_POST
def auto_create_sanad_texts_view(request, hadith_id):
    """
    Automatically create sanad texts for all sanads that don't have them
    """
    hadith = get_object_or_404(Hadith, id=hadith_id)
    
    # Get sanads without texts
    sanads_without_texts = Sanad.objects.filter(
        hadith=hadith
    ).exclude(
        sanad_text__isnull=False
    )
    
    created_count = 0
    for sanad in sanads_without_texts:
        SanadText.objects.create(
            sanad=sanad,
            text=hadith.text,
            variation_notes=_('نسخة تلقائية من النص الأساسي للحديث')
        )
        created_count += 1
    
    messages.success(request, _('تم إنشاء {} نص سند تلقائياً').format(created_count))
    return redirect('hadith_app:hadith_sanad_texts', hadith_id=hadith_id)
