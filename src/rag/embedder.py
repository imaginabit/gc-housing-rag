"""
Embeddings usando sentence-transformers (local, gratis).

Usa el modelo 'all-MiniLM-L6-v2' que produce embeddings de 384 dims.
No requiere API key — funciona 100% en local.
"""
from sentence_transformers import SentenceTransformer
from typing import List

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Cargador perezoso — solo se carga cuando se usa
_model = None


def _get_model():
    """Carga el modelo bajo demanda."""
    global _model
    if _model is None:
        print(f"  🔄 Cargando modelo de embeddings: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Genera embeddings para una lista de textos.
    
    Args:
        texts: Lista de textos a embeber
    
    Returns:
        Lista de vectores de embedding
    """
    if not texts:
        return []
    
    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    
    # Convertir numpy arrays a listas de floats
    return [emb.tolist() for emb in embeddings]


def embed_query(query: str) -> List[float]:
    """
    Genera embedding para una query del usuario.
    """
    embeddings = embed_texts([query])
    return embeddings[0] if embeddings else []


def check_embedding_dim(embedding: List[float]) -> bool:
    """Verifica la dimensión del embedding."""
    return len(embedding) == EMBEDDING_DIM
