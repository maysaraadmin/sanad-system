from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse
from django.apps import apps as django_apps
from django.http import Http404

class CustomAdminSite(AdminSite):
    site_header = _('إدارة نظام السند')
    site_title = _('نظام السند')
    index_title = _('لوحة التحكم')
    
    def get_urls(self):
        from django.urls import include, path
        
        # Get the default URLs
        urls = super().get_urls()
        
        # Add any custom URLs here if needed
        custom_urls = [
            # Add your custom URLs here
        ]
        
        return custom_urls + urls
        
    def each_context(self, request):
        context = super().each_context(request)
        # Add any custom context here if needed
        return context
    
    def _build_app_dict(self, request, app_label=None):
        """
        Build the app dictionary. The optional `app_label` argument filters an
        app of specific interest.
        """
        # Start with the default implementation
        app_dict = {}
        
        if app_label:
            # If a specific app is requested, only process that one
            apps = [app for app in self.get_app_list(request) 
                   if app['app_label'] == app_label]
        else:
            # Otherwise, process all apps
            apps = self.get_app_list(request)
            
        # Process each app
        for app in apps:
            app_label = app['app_label']
            app_dict[app_label] = app
            
            # Sort models within the app
            models = app.get('models', [])
            hadith_models = []
            other_models = []
            
            for model in models:
                if model.get('object_name') in ['Hadith', 'Sanad', 'Narrator', 'SanadNarrator', 'HadithCategory', 'HadithBook']:
                    hadith_models.append(model)
                else:
                    other_models.append(model)
            
            # Apply custom ordering
            app['models'] = hadith_models + other_models
        
        return app_dict
    
    def get_app_list(self, request, app_label=None):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        # Use the parent's implementation to get the app list
        app_list = []
        
        # Get all registered models
        for model, model_admin in self._registry.items():
            app_label = model._meta.app_label
            app_name = model._meta.app_config.verbose_name
            
            # Find or create the app in the app_list
            app = next((app for app in app_list if app['app_label'] == app_label), None)
            if not app:
                app = {
                    'name': app_name,
                    'app_label': app_label,
                    'app_url': f'/admin/{app_label}/',
                    'has_module_perms': True,
                    'models': []
                }
                app_list.append(app)
            
            # Add the model to the app
            model_dict = {
                'name': model._meta.verbose_name_plural,
                'object_name': model._meta.object_name,
                'admin_url': f'/admin/{app_label}/{model._meta.model_name}/',
                'add_url': f'/admin/{app_label}/{model._meta.model_name}/add/',
                'view_only': False
            }
            app['models'].append(model_dict)
        
        # Sort the apps and their models
        for app in app_list:
            app['models'].sort(key=lambda x: x['name'])
        
        app_list.sort(key=lambda x: x['name'].lower())
        
        return app_list

# Create the admin site instance
admin_site = CustomAdminSite(name='admin')

# Register all models with the custom admin site
def register_models():
    from django.apps import apps
    from django.contrib import admin
    from django.contrib.admin.sites import AlreadyRegistered
    
    # Get all models
    for model in apps.get_models():
        try:
            # Skip if already registered
            if model in admin_site._registry:
                continue
                
            # Get the admin class if it exists
            model_admin = admin.site._registry.get(model)
            if model_admin:
                admin_site.register(model, model_admin.__class__)
            else:
                admin_site.register(model)
                
        except AlreadyRegistered:
            pass
        except Exception as e:
            print(f"Error registering {model.__name__}: {e}")

# Register all models
register_models()

# Override the default admin site
admin.site = admin_site
admin.sites.site = admin_site
