from django.utils import translation
from django.conf import settings

class ForceDefaultLanguageMiddleware:
    """
    Force the project's default language for all requests, respecting
    LANGUAGE_CODE from settings rather than a hardcoded value.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.language = getattr(settings, 'LANGUAGE_CODE', 'ar')

    def __call__(self, request):
        translation.activate(self.language)
        request.LANGUAGE_CODE = translation.get_language()

        response = self.get_response(request)

        response['Content-Language'] = self.language
        return response
