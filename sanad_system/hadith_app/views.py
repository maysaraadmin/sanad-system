from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView
from django.contrib import messages
from .models import Hadith, Narrator, Sanad, HadithCategory

class HadithListView(ListView):
    model = Hadith
    template_name = 'hadith_app/hadith_list.html'
    context_object_name = 'hadiths'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        grade = self.request.GET.get('grade')
        category = self.request.GET.get('category')
        
        if grade:
            queryset = queryset.filter(grade=grade)
        if category:
            queryset = queryset.filter(categories__id=category)
            
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = HadithCategory.objects.all()
        context['grades'] = Hadith._meta.get_field('grade').choices
        return context

class HadithDetailView(DetailView):
    model = Hadith
    template_name = 'hadith_app/hadith_detail.html'
    context_object_name = 'hadith'

class NarratorListView(ListView):
    model = Narrator
    template_name = 'hadith_app/narrator_list.html'
    context_object_name = 'narrators'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        reliability = self.request.GET.get('reliability')
        
        if reliability:
            queryset = queryset.filter(reliability=reliability)
            
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reliability_options'] = Narrator._meta.get_field('reliability').choices
        return context

class NarratorDetailView(DetailView):
    model = Narrator
    template_name = 'hadith_app/narrator_detail.html'
    context_object_name = 'narrator'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hadiths'] = Hadith.objects.filter(asanid__narrators=self.object).distinct()
        return context

def search_view(request):
    query = request.GET.get('q', '')
    hadith_results = Hadith.objects.filter(text__icontains=query)
    narrator_results = Narrator.objects.filter(name__icontains=query)
    
    return render(request, 'hadith_app/search_results.html', {
        'query': query,
        'hadith_results': hadith_results,
        'narrator_results': narrator_results,
    })
    
def custom_404_view(request, exception):
    return render(request, 'hadith_app/404.html', status=404)
