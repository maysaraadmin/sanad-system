"""
URL configuration for sanad_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import RedirectView

# Import the custom admin site instance from admin_site.py
from hadith_app.admin_site import admin_site

# Ensure the default admin site is using our custom admin site
admin.site = admin_site
admin.sites.site = admin_site

urlpatterns = [
    # Admin URLs - Using custom admin site
    path('admin/', admin.site.urls),
    
    # Authentication URLs - Using our custom templates
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(
        template_name='registration/logged_out.html',
        next_page='hadith_app:hadith_list'
    ), name='logout'),
    
    # App URLs
    path('', include(('hadith_app.urls', 'hadith_app'), namespace='hadith_app')),
    path('library/', include(('library.urls', 'library'), namespace='library')),
    
    # Redirect /documents/ to /library/ for backward compatibility
    path('documents/', RedirectView.as_view(url='/library/', permanent=True)),
    path('documents/<path:path>/', RedirectView.as_view(pattern_name='library:document_detail', kwargs={'path': '%(path)s'}), name='document_redirect'),
    
    # Language switcher
    path('i18n/', include('django.conf.urls.i18n')),
] 

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)