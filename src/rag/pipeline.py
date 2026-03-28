"""Pipeline principal de indexación RAG.

Coordina la ingestión de datos, generación de chunks,
embeddings e indexación en Pinecone.
"""

import unicodedata
import re
from typing import List, Dict, Any

from ..config import EMBEDDING_DIM
from .embedder import embed_texts
from .indexer import index_data
from .real_chunks import create_all_chunks


def slugify(text: str) -> str:
    """Convierte texto a ID ASCII seguro (sin acentos, sin espacios)."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-zA-Z0-9_]", "_", text)
    return text.lower()


def generate_embeddings(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Genera embeddings para todos los chunks de texto.

    Args:
        chunks: Lista de chunks con campo 'text'

    Returns:
        Lista de chunks con campo 'embedding' añadido
    """
    print(f"\n  🤖 Generando embeddings con MiniMax ({len(chunks)} chunks)...")

    texts = [chunk["text"] for chunk in chunks]

    # Batch embeddings
    batch_size = 20
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        print(f"  ... procesando {min(i + batch_size, len(texts))}/{len(texts)}")

        embeddings = embed_texts(batch)
        all_embeddings.extend(embeddings)

    # Añadir embeddings a chunks
    for chunk, embedding in zip(chunks, all_embeddings):
        chunk["embedding"] = embedding

    # Verificar dimensiones
    if all_embeddings and len(all_embeddings[0]) == EMBEDDING_DIM:
        print(f"  ✅ Embeddings OK ({EMBEDDING_DIM} dim)")
    else:
        print(
            f"  ⚠️ Dimensión inesperada: {len(all_embeddings[0]) if all_embeddings else 0}"
        )

    return chunks


def run_index_pipeline():
    """
    Ejecuta el pipeline completo de indexación:
    1. Crear chunks con datos reales (ISTAC, Doorstep)
    2. Generar embeddings
    3. Indexar en Pinecone
    """
    print("\n" + "=" * 60)
    print("🏗️  PIPELINE DE INDEXACIÓN RAG - GC Housing")
    print("=" * 60)

    # 1. Crear chunks con datos reales
    print("\n[1/3] Creando chunks con datos reales...")
    chunks = create_all_chunks()

    if not chunks:
        print("  ❌ No hay chunks. Comprueba los datos en data/raw/")
        return

    # 2. Generar embeddings
    print("\n[2/3] Generando embeddings...")
    chunks = generate_embeddings(chunks)

    # 3. Indexar en Pinecone
    print("\n[3/3] Indexando en Pinecone...")
    index_data(chunks)

    print("\n" + "=" * 60)
    print("✅ INDEXACIÓN COMPLETA")
    print("=" * 60)


if __name__ == "__main__":
    run_index_pipeline()
