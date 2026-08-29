import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings

@require_POST
def set_theme(request):
    try:
        data = json.loads(request.body)
        theme = data.get('theme', 'light')
        
        # Set theme in session
        request.session['theme'] = theme
        
        # Set cookie that will persist across sessions (1 year expiry)
        response = JsonResponse({'status': 'success', 'theme': theme})
        response.set_cookie(
            'theme',
            value=theme,
            max_age=365 * 24 * 60 * 60,  # 1 year
            secure=request.is_secure(),
            httponly=True,
            samesite='Lax'
        )
        
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'An error occurred while setting theme.'}, status=500)
