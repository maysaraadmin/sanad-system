"""
Contextual Search Module for Hadiths

This module provides contextual search capabilities to find hadiths
based on topics, themes, and other contextual information.
"""
from typing import List, Dict, Any, Optional, Set
from django.db.models import Q, Count
from ..models import Hadith, HadithCategory, Sanad, Narrator
import re

def contextual_search(
    topics: List[str] = None,
    categories: List[int] = None,
    narrators: List[int] = None,
    reliability: List[str] = None,
    time_period: tuple = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search hadiths based on contextual information.
    
    Args:
        topics: List of topics or themes to search for in hadith text and context
        categories: List of category IDs to filter by
        narrators: List of narrator IDs to filter by
        reliability: List of reliability levels to filter by (e.g., ['thiqa', 'saduq'])
        time_period: Tuple of (start_year, end_year) to filter by narrator's lifetime
        limit: Maximum number of results to return
        
    Returns:
        List of hadiths matching the contextual criteria
    """
    queryset = Hadith.objects.all()
    
    # Filter by topics in text or context
    if topics:
        topic_queries = Q()
        for topic in topics:
            topic_queries |= Q(text__icontains=topic) | Q(context__icontains=topic)
        queryset = queryset.filter(topic_queries)
    
    # Filter by categories
    if categories:
        queryset = queryset.filter(categories__in=categories).distinct()
    
    # Filter by narrators and their reliability
    if narrators or reliability:
        sanad_queries = Q()
        
        if narrators:
            sanad_queries &= Q(narrators__in=narrators)
            
        if reliability:
            # Get all narrators with the specified reliability
            reliable_narrators = Narrator.objects.filter(reliability__in=reliability)
            sanad_queries &= Q(narrators__in=reliable_narrators)
        
        # Get hadiths through the Sanad relationship
        hadith_ids = Sanad.objects.filter(sanad_queries).values_list('hadith_id', flat=True).distinct()
        queryset = queryset.filter(id__in=hadith_ids)
    
    # Filter by time period (narrator's lifetime)
    if time_period:
        start_year, end_year = time_period
        period_narrators = Narrator.objects.filter(
            birth_year__lte=end_year,
            death_year__gte=start_year
        )
        hadith_ids = SanadNarrator.objects.filter(
            narrator__in=period_narrators
        ).values_list('sanad__hadith_id', flat=True).distinct()
        queryset = queryset.filter(id__in=hadith_ids)
    
    # Execute query and prepare results
    results = []
    for hadith in queryset.select_related('created_by').prefetch_related('categories')[:limit]:
        results.append({
            'id': hadith.id,
            'text': hadith.text,
            'source': hadith.source,
            'categories': [cat.name for cat in hadith.categories.all()],
            'created_by': hadith.created_by.username if hadith.created_by else None,
            'created_at': hadith.created_at
        })
    
    return results

def extract_topics(text: str) -> List[str]:
    """
    Extract potential topics or themes from a text.
    This is a basic implementation that can be enhanced with NLP.
    """
    # Common Arabic stop words to exclude
    stop_words = {
        'في', 'من', 'عن', 'على', 'إلى', 'أن', 'إن', 'أن', 'ما', 'هذا', 'هذه',
        'هذان', 'هؤلاء', 'ذلك', 'هناك', 'هنا', 'إذا', 'إذن', 'بين', 'عند', 'مع',
        'كل', 'بعض', 'لا', 'نعم', 'كان', 'يكون', 'كانت', 'يكون', 'يكون', 'يكون'
    }
    
    # Extract words (simple tokenization for Arabic)
    words = re.findall(r'[\u0600-\u06FF]+', text)
    
    # Filter out stop words and short words
    words = [w for w in words if len(w) > 2 and w not in stop_words]
    
    # Count word frequencies
    word_counts = {}
    for word in words:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    # Return top 5 most frequent words as potential topics
    return sorted(word_counts, key=word_counts.get, reverse=True)[:5]

def get_hadiths_by_theme(theme: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Find hadiths related to a specific theme by searching in text and context.
    """
    queryset = Hadith.objects.filter(
        Q(text__icontains=theme) | 
        Q(context__icontains=theme) |
        Q(categories__name__icontains=theme)
    ).distinct()
    
    results = []
    for hadith in queryset.select_related('created_by').prefetch_related('categories')[:limit]:
        results.append({
            'id': hadith.id,
            'text': hadith.text,
            'source': hadith.source,
            'categories': [cat.name for cat in hadith.categories.all()],
            'context': hadith.context if hasattr(hadith, 'context') else None
        })
    
    return results
