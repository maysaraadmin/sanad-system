from .sanad_utils import *
from .text_utils import *
from .search_utils import *
from .validation_utils import *
from .user_utils import *

def get_hadith_stats():
    """Get statistics about hadiths in the system"""
    from .models import Hadith
    from django.db.models import Count
    total_hadiths = Hadith.objects.count()
    verified_hadiths = Hadith.objects.filter(grade='sahih').count()
    return {
        'total_hadiths': total_hadiths,
        'verified_hadiths': verified_hadiths,
        'average_hadith_length': Hadith.objects.aggregate(avg_length=Count('text'))['avg_length']
    }

def get_narrator_stats():
    """Get statistics about narrators in the system"""
    from .models import Narrator
    from django.db.models import Avg, F
    total_narrators = Narrator.objects.count()
    reliable_narrators = Narrator.objects.filter(reliability='thiqa').count()
    avg_lifespan = Narrator.objects.filter(
        birth_year__isnull=False,
        death_year__isnull=False
    ).aggregate(avg_years=Avg(F('death_year') - F('birth_year')))['avg_years']
    return {
        'total_narrators': total_narrators,
        'reliable_narrators': reliable_narrators,
        'average_lifespan': round(avg_lifespan, 1) if avg_lifespan is not None else None
    }

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
