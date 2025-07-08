import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.db.models import Q, F, Value, CharField, Count
from django.db.models.functions import Concat
from django.views.decorators.cache import cache_page
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .models import Hadith, Narrator, Sanad, SanadNarrator, HadithCategory, UserProfile
from .forms import HadithForm, ProfileUpdateForm, NarratorForm

class HomeView(TemplateView):
    template_name = 'hadith_app/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['latest_hadiths'] = Hadith.objects.order_by('-created_at')[:5]
        context['popular_narrators'] = Narrator.objects.all()[:5]
        context['narrator_list_url'] = reverse_lazy('hadith_app:narrator_list')
        # Set default theme if not set
        if 'theme' not in self.request.session:
            self.request.session['theme'] = 'auto'
        return context

from django.contrib.sessions.models import Session
from django.utils import timezone
from django.shortcuts import render

from .models import Hadith, Narrator, Sanad, HadithCategory, UserProfile, HadithBook


def custom_404_view(request, exception):
    """Custom 404 error handler."""
    return render(request, '404.html', status=404)


def custom_500_view(request):
    """Custom 500 error handler."""
    return render(request, '500.html', status=500)
from .forms import ProfileUpdateForm, AvatarUploadForm, HadithForm
from .utils import get_hadith_stats, get_narrator_stats


@require_GET
@cache_page(60 * 15)  # Cache for 15 minutes
@require_GET
def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    # Search in hadiths
    hadith_results = Hadith.objects.filter(
        Q(text__icontains=query) |
        Q(source__icontains=query)
    ).values(
        'id', 'text', 'source'
    ).annotate(
        type=Value('hadith', output_field=CharField()),
        display_text=Concat(
            Value('حديث: '),
            'text',
            output_field=CharField()
        )
    )[:5]  # Limit to 5 results
    
    # Search in narrators
    narrator_results = Narrator.objects.filter(
        Q(name__icontains=query) |
        Q(kunya__icontains=query) |
        Q(laqab__icontains=query) |
        Q(biography__icontains=query)
    ).annotate(
        type=Value('narrator', output_field=CharField()),
        display_text=Concat(
            'name',
            Value(' ('),
            F('reliability'),
            Value(')'),
            output_field=CharField()
        )
    ).values('id', 'name', 'reliability', 'type', 'display_text')[:5]  # Limit to 5 results
    
    # Combine and format results
    results = list(hadith_results) + list(narrator_results)
    
    # Sort by relevance (simple length-based sorting for now)
    results.sort(key=lambda x: len(x.get('display_text', '')))
    
    return JsonResponse({
        'results': results[:8]  # Return max 8 combined results
    })


@require_POST
def set_theme(request):
    theme = request.POST.get('theme', 'auto')
    request.session['theme'] = theme
    return JsonResponse({'status': 'ok'})


class HadithCreateView(LoginRequiredMixin, CreateView):
    model = Hadith
    form_class = HadithForm
    template_name = 'hadith_app/hadith_form.html'
    success_url = reverse_lazy('hadith_app:profile')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Save the hadith first
        hadith = form.save(commit=False)
        hadith.created_by = self.request.user
        hadith.save()
        form.save_m2m()  # Save many-to-many relationships (categories)
        
        # Create a Sanad for the hadith
        narrator_chain = form.cleaned_data.get('narrator_chain', '')
        if narrator_chain:
            sanad = Sanad.objects.create(
                hadith=hadith,
                is_mutawatir=False
            )
            
            # Split narrator chain by common separators and create narrators
            # Handle both Arabic and English commas
            narrators = []
            for sep in ['،', ',', ';', '؛']:
                if sep in narrator_chain:
                    narrators = [n.strip() for n in narrator_chain.split(sep) if n.strip()]
                    break
            else:
                narrators = [narrator_chain.strip()]
                
            for i, narrator_name in enumerate(narrators, 1):
                if narrator_name:  # Only process non-empty names
                    # Try to find existing narrator or create a new one
                    narrator, created = Narrator.objects.get_or_create(
                        name=narrator_name,
                        defaults={
                            'reliability': 'unknown',
                            'biography': 'تمت إضافته تلقائياً من خلال إدخال حديث جديد'
                        }
                    )
                    # Add narrator to sanad
                    SanadNarrator.objects.create(
                        sanad=sanad,
                        narrator=narrator,
                        order=i
                    )
        
        messages.success(self.request, _('تمت إضافة الحديث بنجاح'))
        return redirect(self.get_success_url())
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('إضافة حديث جديد')
        context['submit_text'] = _('حفظ الحديث')
        return context


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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hadith = self.get_object()
        
        # Get similar hadiths (from the same source or with similar text)
        similar_hadiths = Hadith.objects.filter(
            Q(source=hadith.source) | 
            Q(text__icontains=hadith.text[:50])  # Simple similarity check
        ).exclude(id=hadith.id).distinct()[:5]  # Limit to 5 similar hadiths
        
        context['similar_hadiths'] = similar_hadiths
        return context


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
        narrator = self.get_object()
        
        # Get hadiths where this narrator is mentioned in the sanad
        hadiths = Hadith.objects.filter(asanid__narrators=narrator).distinct()
        
        # Paginate hadiths
        page = self.request.GET.get('page', 1)
        paginator = Paginator(hadiths, 10)  # 10 hadiths per page
        
        try:
            hadiths_page = paginator.page(page)
        except PageNotAnInteger:
            hadiths_page = paginator.page(1)
        except EmptyPage:
            hadiths_page = paginator.page(paginator.num_pages)
        
        # Get similar narrators (with similar names or from the same time period)
        similar_narrators = Narrator.objects.filter(
            Q(name__icontains=narrator.name.split()[0]) |  # First name match
            Q(birth_year__range=(narrator.birth_year - 50 if narrator.birth_year else None, 
                               narrator.birth_year + 50 if narrator.birth_year else None))
        ).exclude(id=narrator.id).distinct()[:5]  # Limit to 5 similar narrators
        
        context.update({
            'hadiths': hadiths_page,
            'similar_narrators': similar_narrators,
            'paginator': paginator,
        })
        
        return context


def search_view(request):
    query = request.GET.get('q', '').strip()
    
    # Search in hadiths
    hadith_results = Hadith.objects.filter(
        Q(text__icontains=query) |
        Q(source__icontains=query) |
        Q(source_page__icontains=query) |
        Q(source_hadith_number__icontains=query)
    ).distinct()
    
    # Search in narrators
    narrator_results = Narrator.objects.filter(
        Q(name__icontains=query) |
        Q(biography__icontains=query)
    ).distinct()
    
    # Paginate hadith results
    hadith_page = request.GET.get('hadith_page', 1)
    hadith_paginator = Paginator(hadith_results, 10)  # Show 10 hadiths per page
    
    try:
        hadith_results = hadith_paginator.page(hadith_page)
    except PageNotAnInteger:
        hadith_results = hadith_paginator.page(1)
    except EmptyPage:
        hadith_results = hadith_paginator.page(hadith_paginator.num_pages)
    
    # Paginate narrator results
    narrator_page = request.GET.get('narrator_page', 1)
    narrator_paginator = Paginator(narrator_results, 10)  # Show 10 narrators per page
    
    try:
        narrator_results = narrator_paginator.page(narrator_page)
    except PageNotAnInteger:
        narrator_results = narrator_paginator.page(1)
    except EmptyPage:
        narrator_results = narrator_paginator.page(narrator_paginator.num_pages)
    
    context = {
        'query': query,
        'hadith_results': hadith_results,
        'narrator_results': narrator_results,
        'hadith_paginator': hadith_paginator,
        'narrator_paginator': narrator_paginator,
    }
    
    return render(request, 'hadith_app/search_results.html', context)


def custom_404_view(request, exception):
    return render(request, '404.html', status=404)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/profile.html'
    
    def get(self, request, *args, **kwargs):
        # Handle GET requests by setting up the form and rendering the page
        return self.render_to_response(self.get_context_data())
    
    def post(self, request, *args, **kwargs):
        # Handle POST requests for form submission
        context = self.get_context_data()
        
        if context.get('active_tab') == 'settings':
            form = context.get('form')
            if form and form.is_valid():
                return self.form_valid(form)
            
        # If form is invalid or not a settings form, re-render the page with errors
        return self.render_to_response(context)
    
    def form_valid(self, form):
        user = self.request.user
        profile = form.save(commit=False)
        
        # Update user model fields
        user.first_name = form.cleaned_data.get('first_name', '')
        user.last_name = form.cleaned_data.get('last_name', '')
        user.email = form.cleaned_data.get('email', '')
        
        # Handle avatar upload
        if 'avatar' in self.request.FILES:
            # Delete old avatar if it exists
            if profile.avatar:
                profile.avatar.delete(save=False)
            profile.avatar = self.request.FILES['avatar']
        
        # Save both user and profile
        user.save()
        profile.user = user
        profile.save()
        
        messages.success(self.request, _('تم تحديث الملف الشخصي بنجاح'))
        return redirect(reverse('hadith_app:profile') + '?tab=settings')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Get user stats
        hadiths_count = user.hadiths.count() if hasattr(user, 'hadiths') else 0
        bookmarks_count = user.bookmarks.count() if hasattr(user, 'bookmarks') else 0
        
        # Get recent activity
        recent_activity = []
        if hasattr(user, 'hadiths'):
            recent_activity = user.hadiths.order_by('-created_at')[:5]
        
        # Get user's recent bookmarks
        recent_bookmarks = []
        if hasattr(user, 'bookmarks'):
            recent_bookmarks = user.bookmarks.select_related('hadith').order_by('-created_at')[:5]
        
        # Get active tab from URL or default to 'activity'
        active_tab = self.request.GET.get('tab', 'activity')
        
        # Initialize form for settings tab
        if active_tab == 'settings':
            if self.request.method == 'POST':
                form = ProfileUpdateForm(
                    self.request.POST, 
                    self.request.FILES, 
                    instance=profile,
                    initial={
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'email': user.email,
                    }
                )
                if form.is_valid():
                    return self.form_valid(form)
            else:
                form = ProfileUpdateForm(
                    instance=profile,
                    initial={
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'email': user.email,
                    }
                )
            context['form'] = form
        
        context.update({
            'profile': profile,
            'hadiths_count': hadiths_count,
            'bookmarks_count': bookmarks_count,
            'recent_activity': recent_activity,
            'recent_bookmarks': recent_bookmarks,
            'active_tab': active_tab,
            'is_own_profile': True  # Flag to indicate this is the user's own profile
        })
            
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = ProfileUpdateForm
    template_name = 'registration/profile_edit.html'
    success_url = reverse_lazy('hadith_app:profile')
    
    def get_object(self, queryset=None):
        return self.request.user.profile
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.get_form()
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        if hasattr(self, 'object') and self.object:
            kwargs.update({
                'initial': {
                    'first_name': self.object.user.first_name,
                    'last_name': self.object.user.last_name,
                    'email': self.object.user.email,
                }
            })
        return kwargs
    
    def form_valid(self, form):
        # Save the user model first
        user = self.request.user
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.email = form.cleaned_data['email']
        user.save()
        
        # Then save the profile
        response = super().form_valid(form)
        messages.success(self.request, _('تم تحديث الملف الشخصي بنجاح'))
        return response

@login_required
@require_POST
def logout_all_sessions(request):
    """Logout user from all sessions except the current one."""
    # Get all sessions except the current one
    current_session_key = request.session.session_key
    sessions = Session.objects.filter(user=request.user).exclude(session_key=current_session_key)
    
    # Delete all other sessions
    sessions.delete()
    
    messages.success(request, _('تم تسجيل الخروج من جميع الأجهزة الأخرى بنجاح'))
    return redirect(reverse('hadith_app:profile') + '?tab=settings')

@login_required
def delete_account(request):
    """Delete user account and all related data."""
    if request.method == 'POST':
        # Delete user's profile first
        if hasattr(request.user, 'profile'):
            request.user.profile.delete()
        
        # Delete user
        request.user.delete()
        
        messages.success(request, _('تم حذف حسابك بنجاح'))
        return redirect('hadith_app:hadith_list')
    
    return redirect('hadith_app:profile')


@login_required
@require_http_methods(['POST'])
def upload_avatar(request):
    form = AvatarUploadForm(request.POST, request.FILES, instance=request.user.userprofile)
    if form.is_valid():
        # Delete old avatar if exists
        old_avatar = request.user.userprofile.avatar
        if old_avatar and os.path.exists(old_avatar.path):
            os.remove(old_avatar.path)
        
        # Save new avatar
        profile = form.save(commit=False)
        profile.user = request.user
        profile.save()
        
        return JsonResponse({
            'success': True,
            'avatar_url': profile.avatar.url if profile.avatar else ''
        })
    
    return JsonResponse({
        'success': False,
        'errors': form.errors
    }, status=400)


@login_required
@require_http_methods(['POST'])
def set_theme(request):
    try:
        data = json.loads(request.body)
        theme = data.get('theme', 'light')
        
        # Validate theme
        if theme not in ['light', 'dark', 'system']:
            raise ValueError('Invalid theme')
        
        # Save theme preference to user profile
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.theme = theme
        profile.save()
        
        # Set theme in session for immediate feedback
        request.session['theme'] = theme
        
        return JsonResponse({'status': 'success', 'theme': theme})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)