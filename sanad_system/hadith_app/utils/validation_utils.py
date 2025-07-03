from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_year(value):
    """
    Validate that a year is a reasonable value (between 0 and current year + 10).
    """
    from datetime import datetime
    current_year = datetime.now().year
    
    if value < 0 or value > (current_year + 10):
        raise ValidationError(
            _('%(value)s is not a valid year. Year must be between 0 and %(max_year)s'),
            params={'value': value, 'max_year': current_year + 10},
        )

def validate_sanad_text(value):
    """
    Validate the format of sanad text.
    """
    if not value.strip():
        raise ValidationError(_('Sanad text cannot be empty.'))
    
    # Check for minimum number of narrators (at least 2)
    narrators = [n.strip() for n in value.split('\n') if n.strip()]
    if len(narrators) < 2:
        raise ValidationError(_('A sanad must have at least two narrators.'))

def validate_hadith_text(value):
    """
    Validate the format of hadith text.
    """
    if not value.strip():
        raise ValidationError(_('Hadith text cannot be empty.'))
    
    # Minimum length check
    if len(value.strip()) < 10:
        raise ValidationError(_('Hadith text is too short.'))
