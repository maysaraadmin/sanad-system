from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.db.models import Q
from django.core.paginator import Paginator
from ..models import Hadith, Narrator, Sanad, SanadNarrator
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
            search_in = form.cleaned_data.get('search_in', 'all')
            grade_filter = form.cleaned_data.get('grade_filter', [])
            show_sanad = form.cleaned_data.get('show_sanad', False)
            page = self.request.GET.get('page', 1)
            
            hadith_results = []
            narrator_results = []
            
            # Search hadiths
            if search_in in ['all', 'hadith']:
                hadith_queryset = Hadith.objects.all()
                
                # Apply text search
                if query:
                    hadith_queryset = hadith_queryset.filter(
                        Q(text__icontains=query) |
                        Q(source__icontains=query) |
                        Q(source_page__icontains=query) |
                        Q(source_hadith_number__icontains=query)
                    ).distinct()
                
                # Apply grade filter
                if grade_filter:
                    hadith_queryset = hadith_queryset.filter(grade__in=grade_filter)
                
                hadith_results = hadith_queryset.select_related('categories').prefetch_related('sanad_set__narrators')
                
                # Add sanad information if requested
                if show_sanad:
                    hadith_results_with_sanad = []
                    for hadith in hadith_results:
                        sanads = hadith.sanad_set.all().prefetch_related('narrators')
                        hadith_data = {
                            'hadith': hadith,
                            'sanads': sanads,
                        }
                        hadith_results_with_sanad.append(hadith_data)
                    hadith_results = hadith_results_with_sanad
            
            # Search narrators
            if search_in in ['all', 'narrator']:
                narrator_queryset = Narrator.objects.all()
                
                if query:
                    narrator_queryset = narrator_queryset.filter(
                        Q(name__icontains=query) |
                        Q(biography__icontains=query)
                    ).distinct()
                
                narrator_results = narrator_queryset
            
            # Paginate hadith results
            if isinstance(hadith_results, list):
                # For results with sanad data
                paginator = Paginator(hadith_results, 10)
                page_obj = paginator.get_page(page)
                hadith_results = page_obj
            else:
                # For regular queryset
                paginator = Paginator(hadith_results, 10)
                page_obj = paginator.get_page(page)
                hadith_results = page_obj
            
            context.update({
                'query': query,
                'hadith_results': hadith_results,
                'narrator_results': narrator_results,
                'show_sanad': show_sanad,
                'grade_filter': grade_filter,
                'search_in': search_in,
                'paginator': paginator if 'paginator' in locals() else None,
            })
        
        return context
