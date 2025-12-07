"""
Semantic Search Module for Hadiths

This module provides semantic search capabilities using sentence embeddings
to find hadiths based on meaning rather than just keyword matching.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from django.db.models import Q
from ..models import Hadith
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import torch

# Initialize the model (cached for performance)
model = None

def get_embedding_model():
    """Load and cache the sentence transformer model."""
    global model
    if model is None:
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    return model

def get_hadith_embedding(text: str) -> np.ndarray:
    """Get embedding vector for a given hadith text."""
    model = get_embedding_model()
    return model.encode(text, convert_to_numpy=True)

def semantic_search(query: str, threshold: float = 0.5, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Perform semantic search on hadiths using sentence embeddings.
    
    Args:
        query: The search query in natural language
        threshold: Minimum similarity score (0-1) to include in results
        limit: Maximum number of results to return
        
    Returns:
        List of dictionaries containing hadith information and similarity scores
    """
    # Get query embedding
    query_embedding = get_hadith_embedding(query)
    
    # Get all hadiths (in a real app, you'd want to pre-compute and cache these)
    hadiths = list(Hadith.objects.all())
    
    # Get embeddings for all hadiths
    texts = [h.text for h in hadiths]
    text_embeddings = get_embedding_model().encode(texts, convert_to_numpy=True)
    
    # Calculate similarities
    similarities = cosine_similarity(
        [query_embedding],
        text_embeddings
    )[0]
    
    # Combine hadiths with their similarity scores
    results = []
    for hadith, score in zip(hadiths, similarities):
        if score >= threshold:
            results.append({
                'hadith': hadith,
                'score': float(score),
                'text': hadith.text,
                'source': hadith.source,
                'id': hadith.id
            })
    
    # Sort by score (highest first) and limit results
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]

def find_similar_hadiths(hadith_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Find hadiths that are semantically similar to a given hadith.
    
    Args:
        hadith_id: ID of the reference hadith
        limit: Maximum number of similar hadiths to return
        
    Returns:
        List of similar hadiths with similarity scores
    """
    try:
        reference = Hadith.objects.get(id=hadith_id)
    except Hadith.DoesNotExist:
        return []
    
    # Get reference embedding
    ref_embedding = get_hadith_embedding(reference.text)
    
    # Get all other hadiths
    other_hadiths = Hadith.objects.exclude(id=hadith_id)
    
    # Get embeddings and calculate similarities
    texts = [h.text for h in other_hadiths]
    text_embeddings = get_embedding_model().encode(texts, convert_to_numpy=True)
    
    similarities = cosine_similarity(
        [ref_embedding],
        text_embeddings
    )[0]
    
    # Combine and sort results
    results = []
    for hadith, score in zip(other_hadiths, similarities):
        results.append({
            'hadith': hadith,
            'score': float(score),
            'text': hadith.text,
            'source': hadith.source,
            'id': hadith.id
        })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]
