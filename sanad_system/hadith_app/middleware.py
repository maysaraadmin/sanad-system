from django.utils import translation
from django.conf import settings

class ForceDefaultLanguageMiddleware:
    """
    Ignore Accept-Language HTTP header and force the default language for all requests.
    This ensures that the Arabic language is always used.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set the language to Arabic
        language = 'ar'
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
        
        response = self.get_response(request)
        
        # Set the Content-Language header
        response['Content-Language'] = language
        return response
