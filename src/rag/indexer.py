"""
Indexación y query de Pinecone.

Pinecone es un vector store serverless (free tier disponible).
"""
import pinecone
from typing import List, Dict, Any, Optional
from ..config import PINECONE_API_KEY, PINECONE_INDEX, PINECONE_ENV


def init_pinecone():
    """
    Inicializa la conexión con Pinecone.
    """
    pinecone.init(
        api_key=PINECONE_API_KEY,
        environment=PINECONE_ENV
    )


def create_index_if_not_exists(dimension: int = 1536):
    """
    Crea el índice en Pinecone si no existe.
    
    Args:
        dimension: Dimensión de los embeddings (1536 para MiniMax)
    """
    init_pinecone()
    
    if PINECONE_INDEX not in pinecone.list_indexes():
        print(f"  Creando índice '{PINECONE_INDEX}' en Pinecone...")
        pinecone.create_index(
            PINECONE_INDEX,
            dimension=dimension,
            metric="cosine"
        )
        print(f"  ✅ Índice creado")
    else:
        print(f"  ℹ Índice '{PINECONE_INDEX}' ya existe")


def index_data(chunks: List[Dict[str, Any]]):
    """
    Indexa documentos (chunks) en Pinecone.
    
    Cada chunk debe tener:
    - id: identificador único
    - embedding: vector de embedding
    - metadata: dict con text, source, año, barrio, etc.
    
    Args:
        chunks: Lista de dicts con {id, embedding, metadata}
    """
    init_pinecone()
    create_index_if_not_exists()
    
    index = pinecone.Index(PINECONE_INDEX)
    
    # Preparar vectores para upsert
    vectors = []
    for chunk in chunks:
        vectors.append((
            chunk["id"],
            chunk["embedding"],
            chunk.get("metadata", {})
        ))
    
    # Upsert en batches
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        index.upsert(vectors=batch)
        print(f"  📦 Indexados {min(i+batch_size, len(vectors))}/{len(vectors)} chunks")
    
    print(f"  ✅ Indexación completa: {len(vectors)} documentos en '{PINECONE_INDEX}'")


def query_index(
    query_embedding: List[float],
    top_k: int = 5,
    filter_dict: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """
    Query el índice de Pinecone con un embedding.
    
    Args:
        query_embedding: Vector de embedding de la query
        top_k: Número de resultados a devolver
        filter_dict: Filtro opcional (ej: {"barrio": "Vegueta"})
    
    Returns:
        Lista de resultados con {id, score, metadata}
    """
    init_pinecone()
    index = pinecone.Index(PINECONE_INDEX)
    
    result = index.query(
        vector=query_embedding,
        top_k=top_k,
        filter=filter_dict,
        include_metadata=True
    )
    
    return result.get("matches", [])


def delete_all():
    """
    Borra todos los vectores del índice.
    Útil para re-indexar desde cero.
    """
    init_pinecone()
    index = pinecone.Index(PINECONE_INDEX)
    index.delete(delete_all=True)
    print(f"  🗑️  Borrado todos los vectores de '{PINECONE_INDEX}'")
