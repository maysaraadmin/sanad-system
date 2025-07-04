from django.db.models import Count
from .models import Hadith, Narrator

def get_hadith_stats():
    """Get statistics about hadiths in the system"""
    total_hadiths = Hadith.objects.count()
    verified_hadiths = Hadith.objects.filter(grade='sahih').count()
    return {
        'total_hadiths': total_hadiths,
        'verified_hadiths': verified_hadiths,
        'average_hadith_length': Hadith.objects.aggregate(avg_length=Count('text'))['avg_length']
    }

def get_narrator_stats():
    """Get statistics about narrators in the system"""
    total_narrators = Narrator.objects.count()
    reliable_narrators = Narrator.objects.filter(reliability='thiqa').count()
    return {
        'total_narrators': total_narrators,
        'reliable_narrators': reliable_narrators,
        'average_lifespan': Narrator.objects.aggregate(avg_years=Count('death_year') - Count('birth_year'))['avg_years']
    }

from django.db.models import Q
from django.utils import timezone
from .models import Narrator, UserProfile

def get_user_stats(user):
    """Get statistics for a user."""
    # Get count of hadiths created by the user
    hadiths_count = Hadith.objects.filter(created_by=user).count()
    
    # Initialize bookmarks count (to be implemented)
    bookmarks_count = 0
    
    stats = {
        'hadiths_count': hadiths_count,
        'bookmarks_count': bookmarks_count,
        'activity_count': hadiths_count + bookmarks_count,
        'last_activity': Hadith.objects.filter(created_by=user).order_by('-created_at').first().created_at if hadiths_count > 0 else None,
        'profile_completion': 0,
    }
    
    if hasattr(user, 'profile'):
        profile = user.profile
        stats['profile_completion'] = sum(
            bool(getattr(profile, field)) for field in [
                'first_name', 'last_name', 'email', 'avatar', 'bio'
            ]
        ) * 20  # Each field contributes 20% to completion
    
    return stats

def get_similar_narrators(narrator, limit=5):
    """Get similar narrators based on name and time period."""
    # Get similar narrators by first name
    first_name_similar = Narrator.objects.filter(
        name__startswith=narrator.name.split()[0]
    ).exclude(id=narrator.id)
    
    # Get similar narrators by time period
    time_period_similar = Narrator.objects.filter(
        birth_year__range=(narrator.birth_year - 50 if narrator.birth_year else None,
                         narrator.birth_year + 50 if narrator.birth_year else None)
    ).exclude(id=narrator.id)
    
    # Combine and get unique results
    similar = (first_name_similar | time_period_similar).distinct()[:limit]
    return similar

def format_arabic_date(date):
    """Format date in Arabic style."""
    if not date:
        return ''
    
    months = {
        1: 'يناير', 2: 'فبراير', 3: 'مارس',
        4: 'أبريل', 5: 'مايو', 6: 'يونيو',
        7: 'يوليو', 8: 'أغسطس', 9: 'سبتمبر',
        10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
    }
    
    return f"{date.day} {months[date.month]} {date.year}"

def get_user_theme(request):
    """Get user's preferred theme setting."""
    if hasattr(request.user, 'profile'):
        return request.user.profile.theme
    return request.COOKIES.get('theme', 'light')
