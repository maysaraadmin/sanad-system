def menu_items(request):
    return {
        'active_page': request.resolver_match.url_name if hasattr(request, 'resolver_match') else ''
    }