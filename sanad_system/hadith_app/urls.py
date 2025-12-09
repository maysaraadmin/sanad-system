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
from .views.sanad_tree_views import SanadTreeView, sanad_comparison_view, narrator_paths_api
from .views.narrator_analysis_views import (
    narrator_analysis_view, narrator_relationship_network_api, 
    narrator_timeline_api, narrator_geographical_api, 
    narrator_comparison_api, narrator_hadith_paths_api, hadith_comparison_api,
    add_teacher_view, add_teacher_submit, remove_teacher
)
from .views.student_management_views import (
    add_student_view, add_student_submit, remove_student, 
    student_list_view, update_student_notes
)
from .views.hadith_text_views import (
    hadith_texts_view, add_hadith_text_view, add_hadith_text_submit,
    set_primary_text, delete_hadith_text, hadith_text_comparison_view
)
from .views.sanad_narrator_views import (
    sanad_narrators_view, add_sanad_narrator_view, add_sanad_narrator_submit,
    remove_sanad_narrator, reorder_sanad_narrators, update_sanad_narrator
)
from .views.sanad_management_views import (
    SanadUpdateView, SanadDeleteView, sanad_list_view, 
    sanad_duplicate_view, sanad_clear_narrators_view
)
from .views.sanad_text_views import (
    sanad_text_detail_view, SanadTextCreateView, SanadTextUpdateView,
    set_primary_sanad_text_view, hadith_sanad_texts_view, auto_create_sanad_texts_view
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
    
    # Hadith Text Management URLs
    path('hadith/<int:hadith_id>/texts/', hadith_texts_view, name='hadith_texts'),
    path('hadith/<int:hadith_id>/texts/add/', add_hadith_text_view, name='add_hadith_text'),
    path('hadith/<int:hadith_id>/texts/submit/', add_hadith_text_submit, name='add_hadith_text_submit'),
    path('hadith/<int:hadith_id>/texts/<int:text_id>/set-primary/', set_primary_text, name='set_primary_text'),
    path('hadith/<int:hadith_id>/texts/<int:text_id>/delete/', delete_hadith_text, name='delete_hadith_text'),
    path('hadith/<int:hadith_id>/texts/comparison/', hadith_text_comparison_view, name='hadith_text_comparison'),
    
    # Narrator URLs
    path('narrators/', NarratorListView.as_view(), name='narrator_list'),
    path('narrators/create/', NarratorCreateView.as_view(), name='narrator_create'),
    path('narrators/<int:pk>/', NarratorDetailView.as_view(), name='narrator_detail'),
    path('narrators/<int:pk>/update/', NarratorUpdateView.as_view(), name='narrator_update'),
    path('narrators/<int:pk>/delete/', NarratorDeleteView.as_view(), name='narrator_delete'),
    
    # Narrator Analysis URLs
    path('narrator/<int:narrator_id>/analysis/', narrator_analysis_view, name='narrator_analysis'),
    path('narrator/<int:narrator_id>/network/', narrator_relationship_network_api, name='narrator_network'),
    path('narrator/<int:narrator_id>/timeline/', narrator_timeline_api, name='narrator_timeline'),
    path('narrator/<int:narrator_id>/geographical/', narrator_geographical_api, name='narrator_geographical'),
    path('narrator/<int:narrator_id>/comparison/', narrator_comparison_api, name='narrator_comparison'),
    path('narrator/<int:narrator_id>/hadith-paths/', narrator_hadith_paths_api, name='narrator_hadith_paths'),
    
    # Teacher Management URLs
    path('narrator/<int:narrator_id>/teachers/add/', add_teacher_view, name='add_teacher'),
    path('narrator/<int:narrator_id>/teachers/submit/', add_teacher_submit, name='add_teacher_submit'),
    path('narrator/<int:narrator_id>/teachers/<int:teacher_id>/remove/', remove_teacher, name='remove_teacher'),
    
    # Student Management URLs
    path('narrator/<int:narrator_id>/students/add/', add_student_view, name='add_student'),
    path('narrator/<int:narrator_id>/students/submit/', add_student_submit, name='add_student_submit'),
    path('narrator/<int:narrator_id>/students/<int:student_id>/remove/', remove_student, name='remove_student'),
    path('narrator/<int:narrator_id>/students/', student_list_view, name='student_list'),
    path('narrator/<int:narrator_id>/students/<int:student_id>/update-notes/', update_student_notes, name='update_student_notes'),
    
    # Search
    path('search/', SearchView.as_view(), name='search'),
    
    # Sanad URLs
    path('sanad/<int:hadith_id>/add/', SanadCreateView.as_view(), name='sanad_add'),
    path('sanad/<int:hadith_id>/tree/', SanadTreeView.as_view(), name='sanad_tree'),
    path('sanad/<int:hadith_id>/comparison/', sanad_comparison_view, name='sanad_comparison'),
    path('api/narrator/<int:narrator_id>/paths/', narrator_paths_api, name='narrator_paths'),
    path('api/hadith/compare/<str:hadith_ids>/', hadith_comparison_api, name='hadith_comparison'),
    
    # Sanad Management URLs
    path('sanad/<int:pk>/edit/', SanadUpdateView.as_view(), name='sanad_edit'),
    path('sanad/<int:pk>/delete/', SanadDeleteView.as_view(), name='sanad_delete'),
    path('sanad/<int:hadith_id>/list/', sanad_list_view, name='sanad_list'),
    path('sanad/<int:sanad_id>/duplicate/', sanad_duplicate_view, name='sanad_duplicate'),
    path('sanad/<int:sanad_id>/clear-narrators/', sanad_clear_narrators_view, name='sanad_clear_narrators'),
    
    # Sanad Narrator Management URLs
    path('sanad/<int:sanad_id>/narrators/', sanad_narrators_view, name='sanad_narrators'),
    path('sanad/<int:sanad_id>/narrators/add/', add_sanad_narrator_view, name='add_sanad_narrator'),
    path('sanad/<int:sanad_id>/narrators/submit/', add_sanad_narrator_submit, name='add_sanad_narrator_submit'),
    path('sanad/<int:sanad_id>/narrators/<int:narrator_id>/remove/', remove_sanad_narrator, name='remove_sanad_narrator'),
    path('sanad/<int:sanad_id>/narrators/reorder/', reorder_sanad_narrators, name='reorder_sanad_narrators'),
    path('sanad/<int:sanad_id>/narrators/<int:narrator_id>/update/', update_sanad_narrator, name='update_sanad_narrator'),
    
    # Sanad Text Management URLs
    path('sanad/<int:sanad_id>/text/', sanad_text_detail_view, name='sanad_text_detail'),
    path('sanad/<int:sanad_id>/text/create/', SanadTextCreateView.as_view(), name='sanad_text_create'),
    path('sanad/<int:sanad_id>/text/edit/<int:pk>/', SanadTextUpdateView.as_view(), name='sanad_text_edit'),
    path('sanad-text/<int:sanad_text_id>/set-primary/', set_primary_sanad_text_view, name='set_primary_sanad_text'),
    path('hadith/<int:hadith_id>/sanad-texts/', hadith_sanad_texts_view, name='hadith_sanad_texts'),
    path('hadith/<int:hadith_id>/sanad-texts/auto-create/', auto_create_sanad_texts_view, name='auto_create_sanad_texts'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
    
    # Theme
    path('theme/set/', set_theme, name='set_theme'),
    
    # Error Pages
    path('404/', TemplateView.as_view(template_name='404.html'), name='404'),
    path('500/', TemplateView.as_view(template_name='500.html'), name='500'),
]