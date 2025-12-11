"""
Utility functions for RAG app
"""

import warnings
import os

def suppress_warnings():
    """Suppress common warnings for cleaner output"""
    # Suppress transformers deprecation warnings
    warnings.filterwarnings('ignore', category=FutureWarning, module='transformers')
    
    # Suppress huggingface_hub symlink warnings on Windows
    os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
    
    # Suppress distributed multiprocessing warnings on Windows
    os.environ.setdefault('TORCH_DISTRIBUTED_DEBUG', 'OFF')
