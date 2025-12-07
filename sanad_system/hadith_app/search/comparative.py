"""
Comparative Analysis Module for Hadiths

This module provides functionality to compare different narrations of the same hadith,
analyzing variations in text, narrators, and chains of transmission.
"""
from typing import List, Dict, Any, Tuple, Set, Optional
from difflib import SequenceMatcher
from collections import defaultdict
from django.db.models import Q
from ..models import Hadith, Sanad, Narrator, SanadNarrator
import re

def compare_narrations(hadith_ids: List[int]) -> Dict[str, Any]:
    """
    Compare multiple narrations of the same hadith.
    
    Args:
        hadith_ids: List of hadith IDs to compare
        
    Returns:
        Dictionary containing comparison results including:
        - common_text: Text common to all narrations
        - variations: List of variations between narrations
        - narrators: Information about narrators in each chain
        - reliability: Analysis of chain reliability
    """
    if len(hadith_ids) < 2:
        raise ValueError("At least two hadiths are required for comparison")
    
    # Get the hadiths
    hadiths = list(Hadith.objects.filter(id__in=hadith_ids))
    if len(hadiths) != len(hadith_ids):
        raise ValueError("One or more hadiths not found")
    
    # Get all sanads for these hadiths
    sanads = Sanad.objects.filter(hadith__in=hadiths).select_related('hadith')
    
    # Group sanads by hadith
    sanads_by_hadith = defaultdict(list)
    for sanad in sanads:
        sanads_by_hadith[sanad.hadith_id].append(sanad)
    
    # Prepare the results
    results = {
        'hadiths': [],
        'common_text': None,
        'variations': [],
        'narrator_analysis': {},
        'reliability_analysis': {}
    }
    
    # Add basic hadith information
    for hadith in hadiths:
        results['hadiths'].append({
            'id': hadith.id,
            'text': hadith.text,
            'source': hadith.source,
            'sanads': []
        })
    
    # Compare texts to find common parts and variations
    if len(hadiths) >= 2:
        text1 = hadiths[0].text
        text2 = hadiths[1].text
        
        # Find common text using sequence matching
        matcher = SequenceMatcher(None, text1, text2)
        common_blocks = matcher.get_matching_blocks()
        
        # Extract common text (longest common substring)
        if common_blocks:
            _, i, n = max(common_blocks, key=lambda x: x[2])
            results['common_text'] = text1[i:i+n]
        
        # Find variations
        differences = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                diff = {
                    'type': tag,
                    'text1': text1[i1:i2],
                    'text2': text2[j1:j2],
                    'position1': i1,
                    'position2': j1
                }
                differences.append(diff)
        
        results['variations'] = differences
    
    # Analyze narrators and chains
    narrator_chains = {}
    for hadith in hadiths:
        hadith_sanads = sanads_by_hadith.get(hadith.id, [])
        
        for sanad in hadith_sanads:
            # Get narrators in order
            narrators = SanadNarrator.objects.filter(
                sanad=sanad
            ).select_related('narrator').order_by('order')
            
            narrator_chain = [{
                'id': sn.narrator.id,
                'name': sn.narrator.name,
                'reliability': sn.narrator.reliability,
                'order': sn.order,
                'narration_method': sn.narration_method
            } for sn in narrators]
            
            if hadith.id not in narrator_chains:
                narrator_chains[hadith.id] = []
            
            narrator_chains[hadith.id].append(narrator_chain)
    
    results['narrator_chains'] = narrator_chains
    
    # Perform reliability analysis
    reliability_counts = defaultdict(lambda: {'count': 0, 'narrators': []})
    
    for hadith_id, chains in narrator_chains.items():
        for chain in chains:
            for narrator in chain:
                rel = narrator['reliability']
                reliability_counts[rel]['count'] += 1
                if narrator['name'] not in reliability_counts[rel]['narrators']:
                    reliability_counts[rel]['narrators'].append(narrator['name'])
    
    results['reliability_analysis'] = dict(reliability_counts)
    
    return results

def find_related_narrations(hadith_id: int, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Find other narrations of the same hadith based on text similarity.
    
    Args:
        hadith_id: ID of the reference hadith
        similarity_threshold: Minimum text similarity score (0-1) to consider as related
        
    Returns:
        List of related hadiths with similarity scores
    """
    try:
        reference = Hadith.objects.get(id=hadith_id)
    except Hadith.DoesNotExist:
        return []
    
    # Get all other hadiths with similar text length (±20%)
    ref_length = len(reference.text)
    min_length = int(ref_length * 0.8)
    max_length = int(ref_length * 1.2)
    
    candidate_hadiths = Hadith.objects.exclude(id=hadith_id).filter(
        text__length__gte=min_length,
        text__length__lte=max_length
    )
    
    # Simple text similarity comparison
    results = []
    matcher = SequenceMatcher()
    ref_text = reference.text
    
    for hadith in candidate_hadiths:
        matcher.set_seqs(ref_text, hadith.text)
        ratio = matcher.ratio()
        
        if ratio >= similarity_threshold:
            results.append({
                'hadith': hadith,
                'similarity': ratio,
                'text': hadith.text,
                'source': hadith.source,
                'id': hadith.id
            })
    
    # Sort by similarity (highest first)
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results

def analyze_chain_of_narrators(sanad_id: int) -> Dict[str, Any]:
    """
    Analyze the chain of narrators for a given sanad.
    
    Args:
        sanad_id: ID of the sanad to analyze
        
    Returns:
        Dictionary containing analysis of the chain of narrators
    """
    try:
        sanad = Sanad.objects.get(id=sanad_id)
    except Sanad.DoesNotExist:
        return {"error": "Sanad not found"}
    
    # Get all narrators in order
    sanad_narrators = SanadNarrator.objects.filter(
        sanad=sanad
    ).select_related('narrator').order_by('order')
    
    # Prepare chain analysis
    chain = []
    reliability_scores = []
    
    for sn in sanad_narrators:
        narrator = sn.narrator
        reliability = narrator.reliability if narrator else 'unknown'
        
        # Simple reliability scoring (can be enhanced)
        reliability_score = {
            'thiqa': 1.0,
            'saduq': 0.8,
            'weak': 0.4,
            'unknown': 0.2
        }.get(reliability, 0.2)
        
        chain.append({
            'id': narrator.id if narrator else None,
            'name': narrator.name if narrator else 'Unknown',
            'reliability': reliability,
            'reliability_score': reliability_score,
            'order': sn.order,
            'narration_method': sn.narration_method
        })
        
        reliability_scores.append(reliability_score)
    
    # Calculate overall chain reliability
    if reliability_scores:
        # Simple geometric mean of reliability scores
        import math
        log_sum = sum(math.log(score) for score in reliability_scores if score > 0)
        overall_reliability = math.exp(log_sum / len(reliability_scores))
    else:
        overall_reliability = 0.0
    
    return {
        'sanad_id': sanad.id,
        'hadith_id': sanad.hadith.id,
        'chain': chain,
        'overall_reliability': overall_reliability,
        'reliability_interpretation': interpret_reliability(overall_reliability)
    }

def interpret_reliability(score: float) -> str:
    """Interpret the reliability score into a human-readable form."""
    if score >= 0.8:
        return "Very Reliable"
    elif score >= 0.6:
        return "Reliable"
    elif score >= 0.4:
        return "Moderately Reliable"
    elif score >= 0.2:
        return "Weak"
    else:
        return "Very Weak"
