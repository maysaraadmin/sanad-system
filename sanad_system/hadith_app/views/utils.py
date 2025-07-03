def parse_sanad_chain(sanad_text):
    """
    Parse a sanad chain text into individual narrators.
    
    Args:
        sanad_text (str): The sanad chain text with narrators separated by newlines
        
    Returns:
        list: A list of dictionaries containing narrator information
    """
    if not sanad_text:
        return []
    
    # Split the sanad text by newlines and filter out empty lines
    narrator_lines = [line.strip() for line in sanad_text.split('\n') if line.strip()]
    
    # Create a list of narrator dictionaries
    narrators = []
    for i, line in enumerate(narrator_lines, 1):
        narrators.append({
            'name': line,
            'order': i,
        })
    
    return narrators
