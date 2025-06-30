from django.urls import path
from . import views

app_name = 'hadith_app'

urlpatterns = [
    path('', views.HadithListView.as_view(), name='hadith_list'),  # This will handle the root URL
    path('hadith/<int:pk>/', views.HadithDetailView.as_view(), name='hadith_detail'),
    path('narrators/', views.NarratorListView.as_view(), name='narrator_list'),
    path('narrators/<int:pk>/', views.NarratorDetailView.as_view(), name='narrator_detail'),
    path('search/', views.search_view, name='search'),
]