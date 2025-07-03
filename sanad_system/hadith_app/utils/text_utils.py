from typing import List, Dict, Any
from ..models import Narrator

def get_similar_narrators(name: str, threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Find narrators with names similar to the given name.
    
    Args:
        name: The name to search for
        threshold: Similarity threshold (0-1)
        
    Returns:
        List of dictionaries containing narrator information
    """
    from difflib import get_close_matches
    
    # Get all narrator names
    all_narrators = list(Narrator.objects.values('id', 'name'))
    names = [n['name'] for n in all_narrators]
    
    # Find close matches
    matches = get_close_matches(name, names, n=5, cutoff=threshold)
    
    # Return matching narrators with their IDs
    return [n for n in all_narrators if n['name'] in matches]
