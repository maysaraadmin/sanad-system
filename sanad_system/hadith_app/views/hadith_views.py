from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from ..models import Hadith, Sanad, SanadNarrator
from ..forms import HadithForm
from .utils import parse_sanad_chain

class HadithListView(ListView):
    model = Hadith
    template_name = 'hadith_app/hadith_list.html'
    context_object_name = 'hadiths'
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '')
        if search_query:
            queryset = queryset.filter(
                Q(text__icontains=search_query) |
                Q(source__icontains=search_query) |
                Q(source_hadith_number__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context

class HadithDetailView(DetailView):
    model = Hadith
    template_name = 'hadith_app/hadith_detail.html'
    context_object_name = 'hadith'

class HadithCreateView(LoginRequiredMixin, CreateView):
    model = Hadith
    form_class = HadithForm
    template_name = 'hadith_app/hadith_form.html'
    success_url = reverse_lazy('hadith_app:hadith_list')

    def form_valid(self, form):
        # Parse sanad chain and create related objects
        sanad_text = form.cleaned_data.get('sanad_text')
        if sanad_text:
            sanad = Sanad.objects.create(hadith=self.object)
            parse_sanad_chain(sanad_text, sanad)
        
        messages.success(self.request, _('Hadith created successfully'))
        return super().form_valid(form)

class HadithUpdateView(LoginRequiredMixin, UpdateView):
    model = Hadith
    form_class = HadithForm
    template_name = 'hadith_app/hadith_form.html'
    success_url = reverse_lazy('hadith_app:hadith_list')

    def form_valid(self, form):
        messages.success(self.request, _('Hadith updated successfully'))
        return super().form_valid(form)

class HadithDeleteView(LoginRequiredMixin, DeleteView):
    model = Hadith
    template_name = 'hadith_app/hadith_confirm_delete.html'
    success_url = reverse_lazy('hadith_app:hadith_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Hadith deleted successfully'))
        return super().delete(request, *args, **kwargs)
