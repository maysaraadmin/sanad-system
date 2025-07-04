from django.urls import path
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import views as auth_views
from .views import (
    HadithListView, HadithDetailView, HadithCreateView, HadithUpdateView, HadithDeleteView,
    NarratorListView, NarratorDetailView,
    LoginView, LogoutView, RegisterView,
    ProfileView, ProfileUpdateView,
    SearchView,
)

app_name = 'hadith_app'

urlpatterns = [
    # Home
    path('', TemplateView.as_view(template_name='hadith_app/home.html'), name='home'),
    
    # Authentication
    path('accounts/register/', RegisterView.as_view(), name='register'),
    path('accounts/login/', LoginView.as_view(), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='hadith_app/password_reset_form.html',
        email_template_name='hadith_app/password_reset_email.html',
        subject_template_name='hadith_app/password_reset_subject.txt'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='hadith_app/password_reset_done.html'
    ), name='password_reset_done'),
    
    # Hadith URLs
    path('hadith/', HadithListView.as_view(), name='hadith_list'),
    path('hadith/<int:pk>/', HadithDetailView.as_view(), name='hadith_detail'),
    path('hadith/create/', HadithCreateView.as_view(), name='hadith_create'),
    path('hadith/<int:pk>/update/', HadithUpdateView.as_view(), name='hadith_update'),
    path('hadith/<int:pk>/delete/', HadithDeleteView.as_view(), name='hadith_delete'),
    
    # Narrator URLs
    path('narrators/', NarratorListView.as_view(), name='narrator_list'),
    path('narrators/<int:pk>/', NarratorDetailView.as_view(), name='narrator_detail'),
    
    # Search
    path('search/', SearchView.as_view(), name='search'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
    
    # Error Pages
    path('404/', TemplateView.as_view(template_name='404.html'), name='404'),
    path('500/', TemplateView.as_view(template_name='500.html'), name='500'),
    path('password_reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='hadith_app/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password_reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='hadith_app/password_reset_complete.html'), name='password_reset_complete'),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='hadith_app/password_change.html'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='hadith_app/password_change_done.html'), name='password_change_done'),
]