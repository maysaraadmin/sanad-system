from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class HadithAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hadith_app'
    verbose_name = _('Hadith System')
    
    def ready(self):
        import hadith_app.signals  # Import signals
        
        # Register any app-specific checks
        from django.core.checks import register
        from .checks import hadith_app_checks
        register(hadith_app_checks)
    
    def ready(self):
        import hadith_app.signals
