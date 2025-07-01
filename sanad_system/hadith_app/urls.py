from django.urls import path
from . import views

app_name = 'hadith_app'

urlpatterns = [
    path('', views.HadithListView.as_view(), name='hadith_list'),
    path('hadith/<int:pk>/', views.HadithDetailView.as_view(), name='hadith_detail'),
    path('narrators/', views.NarratorListView.as_view(), name='narrator_list'),
    path('narrators/<int:pk>/', views.NarratorDetailView.as_view(), name='narrator_detail'),
    path('search/', views.search_view, name='search'),
    path('set-theme/', views.set_theme, name='set_theme'),
]