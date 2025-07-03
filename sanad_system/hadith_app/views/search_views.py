from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.db.models import Q
from ..models import Hadith, Narrator
from ..forms import SearchForm

class SearchView(TemplateView):
    template_name = 'hadith_app/search_results.html'

    def get(self, request, *args, **kwargs):
        form = SearchForm(request.GET)
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = kwargs.get('form')
        
        if form and form.is_valid():
            query = form.cleaned_data.get('q', '')
            
            # Search hadiths
            hadith_results = Hadith.objects.filter(
                Q(text__icontains=query) |
                Q(source__icontains=query) |
                Q(source_page__icontains=query) |
                Q(source_hadith_number__icontains=query)
            ).distinct()
            
            # Search narrators
            narrator_results = Narrator.objects.filter(
                Q(name__icontains=query) |
                Q(biography__icontains=query)
            ).distinct()
            
            context.update({
                'query': query,
                'hadith_results': hadith_results,
                'narrator_results': narrator_results,
            })
        
        return context
