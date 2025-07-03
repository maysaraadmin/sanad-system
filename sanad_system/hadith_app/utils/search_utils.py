from typing import List, Dict, Any
from ..models import Hadith, Narrator, Sanad

def search_hadith(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for hadiths containing the query text.
    
    Args:
        query: The search query
        limit: Maximum number of results to return
        
    Returns:
        List of dictionaries containing hadith information
    """
    results = Hadith.objects.filter(text__icontains=query).select_related('created_by')[:limit]
    
    return [{
        'id': h.id,
        'text': h.text,
        'source': h.source,
        'created_by': h.created_by.username if h.created_by else None,
        'created_at': h.created_at
    } for h in results]

def search_narrators(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for narrators by name.
    
    Args:
        query: The search query
        limit: Maximum number of results to return
        
    Returns:
        List of dictionaries containing narrator information
    """
    results = Narrator.objects.filter(name__icontains=query)[:limit]
    
    return [{
        'id': n.id,
        'name': n.name,
        'reliability': n.get_reliability_display(),
        'biography': n.biography
    } for n in results]
