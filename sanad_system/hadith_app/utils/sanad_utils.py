from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from ..models import Sanad, Narrator, SanadNarrator, Hadith
import re
from collections import Counter

def parse_sanad_chain(sanad_text: str, sanad: Sanad) -> None:
    """
    Parse a sanad chain text and create related narrator objects.
    
    Args:
        sanad_text: The text containing the sanad chain
        sanad: The Sanad object to associate narrators with
    """
    narrator_names = re.split(r'[\n\r]+', sanad_text.strip())
    
    for position, name in enumerate(narrator_names, start=1):
        narrator, created = Narrator.objects.get_or_create(name=name.strip())
        SanadNarrator.objects.create(
            sanad=sanad,
            narrator=narrator,
            position=position
        )

def validate_sanad_chain(sanad_text: str) -> None:
    """
    Validate the format of a sanad chain text.
    
    Args:
        sanad_text: The text containing the sanad chain
        
    Raises:
        ValidationError: If the sanad chain format is invalid
    """
    if not sanad_text.strip():
        raise ValidationError(_('Sanad chain cannot be empty'))
    
    narrator_names = re.split(r'[\n\r]+', sanad_text.strip())
    if len(narrator_names) < 2:
        raise ValidationError(_(
            'Sanad chain must contain at least two narrators'
        ))
    
    if any(not name.strip() for name in narrator_names):
        raise ValidationError(_('Narrator names cannot be empty'))

def validate_chronological_overlap(sanad: Sanad) -> dict:
    """
    Validate that consecutive narrators in a sanad chain could have met.
    Based on ilm al-rijal: Bukhari required confirmed meeting, Muslim accepted contemporaneity.
    
    Args:
        sanad: The Sanad object to validate
        
    Returns:
        dict with 'valid', 'issues', and 'warnings'
    """
    narrators = list(sanad.narrators.all().order_by('order'))
    issues = []
    warnings = []
    
    for i in range(len(narrators) - 1):
        current = narrators[i].narrator
        next_narr = narrators[i + 1].narrator
        
        # Both need birth/death years to validate
        if not current.birth_year or not next_narr.birth_year:
            warnings.append(
                f"'{current.name}' or '{next_narr.name}' missing birth year - cannot verify chronology"
            )
            continue
        
        current_start = current.birth_year
        current_end = current.death_year or current.birth_year + 120
        next_start = next_narr.birth_year
        next_end = next_narr.death_year or next_narr.birth_year + 120
        
        # Check if there's any overlap in their lifetimes
        overlap_start = max(current_start, next_start)
        overlap_end = min(current_end, next_end)
        
        if overlap_start > overlap_end:
            issues.append(
                f"'{current.name}' ({current_start}-{current_end}) and '{next_narr.name}' "
                f"({next_start}-{next_end}) have no chronological overlap"
            )
        elif overlap_end - overlap_start < 10:
            warnings.append(
                f"'{current.name}' and '{next_narr.name}' only overlapped for ~{overlap_end - overlap_start} years - weak meeting possibility"
            )
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings
    }

def detect_tadlis(sanad: Sanad) -> list:
    """
    Detect potential tadlis in a sanad chain.
    Tadlis occurs when a narrator says 'an X' implying direct hearing
    when they actually heard it indirectly or did not meet the source.
    
    Args:
        sanad: The Sanad object to check
        
    Returns:
        list of dicts with suspected tadlis instances
    """
    narrators = list(sanad.narrators.all().order_by('order'))
    suspected = []
    
    for i in range(len(narrators) - 1):
        current = narrators[i].narrator
        next_narr = narrators[i + 1].narrator
        method = narrators[i].narration_method or ''
        
        # Check if they used direct hearing words like 'حدثنا', 'سمعت', 'أخبرنا'
        direct_indicators = ['حدثنا', 'سمعت', 'أخبرنا', 'سألنا']
        implies_direct = any(ind in method for ind in direct_indicators)
        
        if implies_direct:
            # Verify chronological possibility
            if current.birth_year and next_narr.birth_year:
                current_end = current.death_year or current.birth_year + 120
                next_start = next_narr.birth_year
                
                if current_end < next_start:
                    suspected.append({
                        'narrator': current.name,
                        'source': next_narr.name,
                        'method': method,
                        'reason': f"'{current.name}' died before '{next_narr.name}' was born, but claims direct hearing"
                    })
                elif current.birth_year > (next_narr.death_year or next_narr.birth_year + 120):
                    suspected.append({
                        'narrator': current.name,
                        'source': next_narr.name,
                        'method': method,
                        'reason': f"'{current.name}' born after '{next_narr.name}' died, but claims direct hearing"
                    })
    
    return suspected

def detect_shadh(hadith: Hadith) -> dict:
    """
    Detect if a hadith is shadh (anomalous) based on narrator reliability.
    A hadith is shadh if a reliable narrator contradicts more reliable narrators.
    
    Args:
        hadith: The Hadith object to check
        
    Returns:
        dict with anomaly analysis
    """
    try:
        sanads = hadith.asanid.all().prefetch_related('narrators__narrator')
    except Exception:
        return {'is_shadh': False, 'score': 0.0, 'reasons': []}
    
    reasons = []
    anomaly_score = 0.0
    
    for sanad in sanads:
        narrators = list(sanad.narrators.all().order_by('order'))
        
        for i, sn in enumerate(narrators):
            narrator = sn.narrator
            if narrator.reliability in ['weak', 'mawdu']:
                # Check if this narrator contradicts stronger narrators in other chains
                anomaly_score += 0.3
                reasons.append(
                    f"Weak narrator '{narrator.name}' in sanad chain"
                )
            
            if sn.is_tadlis:
                anomaly_score += 0.2
                reasons.append(f"Tadlis detected from '{narrator.name}'")
            
            if sn.is_mursal:
                anomaly_score += 0.1
                reasons.append(f"Mursal (broken chain) from '{narrator.name}'")
    
    # Cap score at 1.0
    anomaly_score = min(anomaly_score, 1.0)
    
    return {
        'is_shadh': anomaly_score >= 0.5,
        'score': anomaly_score,
        'reasons': reasons[:5]
    }

def detect_mutawatir(hadith: Hadith) -> dict:
    """
    Detect if a hadith is mutawatir (reported by numerous independent chains).
    A hadith is mutawatir if it appears in multiple independent books/sources
    with different sanads.
    
    Args:
        hadith: The Hadith object to check
        
    Returns:
        dict with mutawatir analysis
    """
    # Count unique sources and sanads
    sources = set()
    sanads = hadith.asanid.all()
    
    for sanad in sanads:
        for sn in sanad.narrators.all():
            narrator = sn.narrator
            if narrator.birth_place:
                sources.add(narrator.birth_place)
    
    # Also check other hadiths with same text in different books
    similar_hadiths = Hadith.objects.filter(
        text__icontains=hadith.text[:50]
    ).exclude(id=hadith.id).count()
    
    total_chains = sanads.count() + similar_hadiths
    unique_narrators = set()
    for sanad in sanads:
        for sn in sanad.narrators.all():
            unique_narrators.add(sn.narrator.id)
    
    is_mutawatir = total_chains >= 3 and len(unique_narrators) >= 3
    
    return {
        'is_mutawatir': is_mutawatir,
        'total_chains': total_chains,
        'unique_narrators': len(unique_narrators),
        'confidence': min(total_chains / 5.0, 1.0)
    }

def get_sanad_chain_text(sanad: Sanad) -> str:
    """
    Generate a formatted text representation of the sanad chain.
    
    Args:
        sanad: The Sanad object to get the chain from
        
    Returns:
        str: Formatted sanad chain text
    """
    narrators = sanad.narrators.all().order_by('order')
    return ' -> '.join(narrator.narrator.name for narrator in narrators)

def get_sanad_chain_length(sanad: Sanad) -> int:
    """
    Get the length of the sanad chain (number of narrators).
    
    Args:
        sanad: The Sanad object to check
        
    Returns:
        int: Number of narrators in the chain
    """
    return sanad.narrators.count()
