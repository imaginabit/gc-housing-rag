"""
Indexación y query de Pinecone (v3 API).

Pinecone es un vector store serverless (free tier disponible).
"""

import logging

import pinecone
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional

from ..config import PINECONE_API_KEY, PINECONE_INDEX, PINECONE_ENV

logger = logging.getLogger(__name__)


def get_pinecone_client() -> Pinecone:
    """Devuelve instancia de Pinecone."""
    return Pinecone(api_key=PINECONE_API_KEY)


def create_index_if_not_exists(dimension: int = None):
    """
    Crea el índice en Pinecone si no existe.
    NO borra el índice existente — usa upsert para actualizar datos.
    """
    from ..config import EMBEDDING_DIM

    dim = dimension or EMBEDDING_DIM

    pc = get_pinecone_client()
    index_name = PINECONE_INDEX

    if index_name in pc.list_indexes().names():
        logger.info("Índice '%s' ya existe, reutilizando", index_name)
        return

    logger.info("Creando índice '%s' (dim=%d)", index_name, dim)
    pc.create_index(
        name=index_name,
        dimension=dim,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=PINECONE_ENV or "us-east-1"),
    )
    logger.info("Índice '%s' creado", index_name)


def index_data(chunks: List[Dict[str, Any]]):
    """
    Indexa documentos (chunks) en Pinecone.
    """
    pc = get_pinecone_client()
    create_index_if_not_exists()

    index = pc.Index(PINECONE_INDEX)

    vectors = []
    for chunk in chunks:
        # Convert numpy floats to native Python floats for JSON serialization
        embedding = chunk["embedding"]
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()

        # Also convert any numpy types in metadata
        metadata = {}
        for k, v in chunk.get("metadata", {}).items():
            if hasattr(v, "item"):  # numpy type
                v = v.item()
            metadata[k] = v

        vectors.append({"id": chunk["id"], "values": embedding, "metadata": metadata})

    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        index.upsert(vectors=batch)
        logger.debug("Indexados %d/%d", min(i + batch_size, len(vectors)), len(vectors))

    logger.info("Indexación completa: %d documentos", len(vectors))


def query_index(
    query_embedding: List[float], top_k: int = 5, filter_dict: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """
    Query el índice de Pinecone con un embedding.
    """
    pc = get_pinecone_client()
    index = pc.Index(PINECONE_INDEX)

    result = index.query(
        vector=query_embedding, top_k=top_k, filter=filter_dict, include_metadata=True
    )

    return result.get("matches", [])


def delete_all():
    """Borra todos los vectores del índice."""
    pc = get_pinecone_client()
    index = pc.Index(PINECONE_INDEX)
    index.delete(delete_all=True)
    logger.info("Borrado todos los vectores")
