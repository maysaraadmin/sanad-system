from django.core.exceptions import ValidationError
from ..models import Sanad, Narrator, SanadNarrator
import re

def parse_sanad_chain(sanad_text: str, sanad: Sanad) -> None:
    """
    Parse a sanad chain text and create related narrator objects.
    
    Args:
        sanad_text: The text containing the sanad chain
        sanad: The Sanad object to associate narrators with
    """
    # Split the text into individual narrator names
    narrator_names = re.split(r'[\n\r]+', sanad_text.strip())
    
    # Create or get narrator objects and add them to the sanad
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
    
    # Check for empty narrator names
    if any(not name.strip() for name in narrator_names):
        raise ValidationError(_('Narrator names cannot be empty'))

def get_sanad_chain_text(sanad: Sanad) -> str:
    """
    Generate a formatted text representation of the sanad chain.
    
    Args:
        sanad: The Sanad object to get the chain from
        
    Returns:
        str: Formatted sanad chain text
    """
    narrators = sanad.narrators.all().order_by('position')
    return '\n'.join(narrator.name for narrator in narrators)

def get_sanad_chain_length(sanad: Sanad) -> int:
    """
    Get the length of the sanad chain (number of narrators).
    
    Args:
        sanad: The Sanad object to check
        
    Returns:
        int: Number of narrators in the chain
    """
    return sanad.narrators.count()
