from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from ..models import UserProfile
from ..forms import ProfileUpdateForm
from ..utils import get_user_stats

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'hadith_app/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Get user stats
        stats = get_user_stats(user)
        
        # Get recent activity
        recent_activity = user.hadiths.order_by('-created_at')[:5]
        recent_bookmarks = user.bookmarks.select_related('hadith').order_by('-created_at')[:5]
        
        context.update({
            'profile': profile,
            'stats': stats,
            'recent_activity': recent_activity,
            'recent_bookmarks': recent_bookmarks,
            'is_own_profile': True,
        })
        
        return context

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = ProfileUpdateForm
    template_name = 'hadith_app/profile_edit.html'
    success_url = reverse_lazy('hadith_app:profile')

    def get_object(self, queryset=None):
        return self.request.user.profile

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('تم تحديث الملف الشخصي بنجاح'))
        return response
