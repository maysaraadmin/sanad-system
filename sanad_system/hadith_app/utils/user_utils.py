from django.db.models import Count
from ..models import Hadith, Sanad

def get_user_stats(user):
    """
    Get statistics for a user's contributions.
    
    Args:
        user: The user to get statistics for
        
    Returns:
        dict: A dictionary containing user statistics
    """
    if not user or not user.is_authenticated:
        return {}
        
    # Count hadiths added by the user
    hadith_count = Hadith.objects.filter(created_by=user).count()
    
    # Count sanads added by the user
    sanad_count = Sanad.objects.filter(hadith__created_by=user).count()
    
    # Get the user's most recent contributions
    recent_hadiths = Hadith.objects.filter(
        created_by=user
    ).order_by('-created_at')[:5]
    
    return {
        'hadith_count': hadith_count,
        'sanad_count': sanad_count,
        'recent_hadiths': recent_hadiths,
    }
