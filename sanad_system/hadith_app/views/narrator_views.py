from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from ..models import Narrator, Hadith
from ..forms import NarratorForm
from ..utils import get_similar_narrators

class NarratorListView(ListView):
    model = Narrator
    template_name = 'hadith_app/narrator_list.html'
    context_object_name = 'narrators'
    paginate_by = 20
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '')
        reliability = self.request.GET.get('reliability')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(biography__icontains=search_query)
            )
            
        if reliability:
            queryset = queryset.filter(reliability=reliability)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        
        # Add reliability options to context
        context['reliability_options'] = [
            ('thiqa', 'ثقة'),
            ('saduq', 'صدوق'),
            ('weak', 'ضعيف'),
            ('unknown', 'مجهول')
        ]
        
        return context

class NarratorDetailView(DetailView):
    model = Narrator
    template_name = 'hadith_app/narrator_detail.html'
    context_object_name = 'narrator'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        narrator = self.get_object()
        
        # Get hadiths where this narrator is mentioned through SanadNarrator
        hadiths = Hadith.objects.filter(
            asanid__narrators=narrator
        ).distinct()
        
        # Get similar narrators by name
        similar_narrators = get_similar_narrators(narrator.name) if narrator.name else []
        
        # Add pagination
        paginator = Paginator(hadiths, 10)
        page = self.request.GET.get('page')
        try:
            hadiths_page = paginator.page(page)
        except PageNotAnInteger:
            hadiths_page = paginator.page(1)
        except EmptyPage:
            hadiths_page = paginator.page(paginator.num_pages)
        
        context.update({
            'hadiths': hadiths_page,
            'similar_narrators': similar_narrators,
            'paginator': paginator,
        })
        return context
        
        return context
