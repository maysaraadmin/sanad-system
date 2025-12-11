from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api, views

router = DefaultRouter()
router.register(r'queries', api.RAGQueryViewSet, basename='rag-queries')
router.register(r'configurations', api.RAGConfigurationViewSet, basename='rag-configurations')

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    path('api/ask/', api.AskQuestionView.as_view(), name='rag-ask'),
    path('api/search/', api.SearchHadithsView.as_view(), name='rag-search'),
    path('api/index/', api.IndexHadithsView.as_view(), name='rag-index'),
    path('api/stats/', api.rag_stats, name='rag-stats'),
    path('api/reindex/', api.reindex_all, name='rag-reindex'),
    
    # Web URLs
    path('', views.RAGHomeView.as_view(), name='rag-home'),
    path('ask/', views.ask_question_view, name='rag-ask-question'),
    path('search/', views.search_hadiths_ajax, name='rag-search-ajax'),
    path('history/', views.RAGQueryHistoryView.as_view(), name='rag-query-history'),
    path('admin/', views.admin_dashboard, name='rag-admin-dashboard'),
    path('admin/index/', views.index_hadiths_view, name='rag-index-hadiths'),
    path('admin/reindex/', views.reindex_all_view, name='rag-reindex-all'),
]
