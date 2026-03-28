---
name: rag-pipeline
description: Run the RAG indexing pipeline for GC Housing RAG
disable-model-invocation: true
---

# RAG Pipeline Skill

Ejecuta el pipeline de indexación RAG para el proyecto GC Housing RAG.

## Usage

```
/rag-pipeline
```

## What It Does

1. **Load Data**: Carga los datos procesados de INE y Turismo
2. **Create Chunks**: Genera chunks de texto por barrio
3. **Generate Embeddings**: Crea embeddings usando sentence-transformers
4. **Index Data**: Sube los vectores a Pinecone

## Prerequisites

- Python virtual environment activated
- `.env` configured with:
  - `MINIMAX_API_KEY`
  - `PINECONE_API_KEY`
  - `PINECONE_INDEX`
- Data already ingested in `data/processed/`

## Command

```bash
python -m src.rag.pipeline
```

## Notes

- The pipeline reads from `data/processed/`
- Outputs vectors to Pinecone index configured in `.env`
- Chunk structure includes: id, text, metadata (barrio, source, tipo, año)
