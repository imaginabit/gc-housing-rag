"""
Embeddings usando la API de MiniMax.

MiniMax proporciona modelos de embedding a través de su API.
El modelo `embo-01` produce embeddings de 1536 dimensiones.
"""
import httpx
from typing import List
from ..config import MINIMAX_API_KEY, MINIMAX_BASE_URL, EMBEDDING_MODEL, EMBEDDING_DIM


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Genera embeddings para una lista de textos usando MiniMax API.
    
    Args:
        texts: Lista de textos a embeber
    
    Returns:
        Lista de vectores de embedding (lista de floats)
    """
    if not texts:
        return []
    
    url = f"{MINIMAX_BASE_URL}/embeddings"
    
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # MiniMax embedding API
    payload = {
        "model": EMBEDDING_MODEL,
        "input": texts
    }
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # Extraer los embeddings de la respuesta
        embeddings = []
        for item in data.get("data", []):
            embedding = item.get("embedding", [])
            embeddings.append(embedding)
        
        return embeddings


def embed_query(query: str) -> List[float]:
    """
    Genera embedding para una query del usuario.
    
    Args:
        query: Texto de la pregunta del usuario
    
    Returns:
        Vector de embedding (lista de floats)
    """
    embeddings = embed_texts([query])
    return embeddings[0] if embeddings else []


def check_embedding_dim(embedding: List[float]) -> bool:
    """
    Verifica que el embedding tiene la dimensión correcta.
    """
    return len(embedding) == EMBEDDING_DIM
