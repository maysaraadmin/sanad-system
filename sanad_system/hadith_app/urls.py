from django.urls import path
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import views as auth_views
from .views import (
    HadithListView, HadithDetailView, HadithCreateView, HadithUpdateView, HadithDeleteView,
    NarratorListView, NarratorDetailView, NarratorCreateView, NarratorUpdateView, NarratorDeleteView,
    RegisterView, ProfileView, ProfileUpdateView,
    SearchView, set_theme, SanadCreateView
)

app_name = 'hadith_app'

urlpatterns = [
    # Home
    path('', TemplateView.as_view(template_name='hadith_app/home.html'), name='home'),
    
    # Authentication
    path('accounts/register/', RegisterView.as_view(), name='register'),
    
    # Password reset - using default Django templates
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt'
         ), name='password_reset'),
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'
         ), name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), name='password_reset_complete'),
    path('password_change/', 
         auth_views.PasswordChangeView.as_view(
             template_name='registration/password_change.html'
         ), name='password_change'),
    path('password_change/done/', 
         auth_views.PasswordChangeDoneView.as_view(
             template_name='registration/password_change_done.html'
         ), name='password_change_done'),
    
    # Hadith URLs
    path('hadith/', HadithListView.as_view(), name='hadith_list'),
    path('hadith/<int:pk>/', HadithDetailView.as_view(), name='hadith_detail'),
    path('hadith/create/', HadithCreateView.as_view(), name='hadith_create'),
    path('hadith/<int:pk>/update/', HadithUpdateView.as_view(), name='hadith_update'),
    path('hadith/<int:pk>/delete/', HadithDeleteView.as_view(), name='hadith_delete'),
    
    # Narrator URLs
    path('narrators/', NarratorListView.as_view(), name='narrator_list'),
    path('narrators/create/', NarratorCreateView.as_view(), name='narrator_create'),
    path('narrators/<int:pk>/', NarratorDetailView.as_view(), name='narrator_detail'),
    path('narrators/<int:pk>/update/', NarratorUpdateView.as_view(), name='narrator_update'),
    path('narrators/<int:pk>/delete/', NarratorDeleteView.as_view(), name='narrator_delete'),
    
    # Search
    path('search/', SearchView.as_view(), name='search'),
    
    # Sanad URLs
    path('sanad/create/<int:hadith_id>/', SanadCreateView.as_view(), name='sanad_create'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
    
    # Theme
    path('theme/set/', set_theme, name='set_theme'),
    
    # Error Pages
    path('404/', TemplateView.as_view(template_name='404.html'), name='404'),
    path('500/', TemplateView.as_view(template_name='500.html'), name='500'),
]