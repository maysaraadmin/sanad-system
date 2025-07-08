# This file makes this directory a Python package

# Import the register function to make it available when the package is imported
from .pdf_reader_tags import register

# Make the register function available at the package level
__all__ = ['register']
