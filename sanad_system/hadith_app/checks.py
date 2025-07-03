from django.core.checks import Error, register
from django.conf import settings

@registry.register
@registry.tags('hadith_app')
def hadith_app_checks(app_configs, **kwargs):
    errors = []
    
    # Check if required settings are configured
    required_settings = [
        'MEDIA_URL',
        'MEDIA_ROOT',
        'STATIC_URL',
        'STATIC_ROOT',
    ]
    
    for setting in required_settings:
        if not hasattr(settings, setting):
            errors.append(
                Error(
                    f'Missing required setting: {setting}',
                    hint=f'Please add {setting} to your settings.py',
                    id='hadith_app.E001',
                )
            )
    
    return errors
