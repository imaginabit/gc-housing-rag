# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**GC Housing RAG** — Chatbot con RAG + mapa interactivo para visualizar el impacto de las viviendas vacacionales en los barrios de Las Palmas de Gran Canaria.

- **Stack**: FastAPI + Pinecone + sentence-transformers (local) + Groq LLM + Leaflet.js
- **Purpose**: Analizar turistificación en LPGC con datos de INE (población) y Registro Turismo Canarias

## Commands

### Setup
```bash
cd ~/projects/gc-housing-rag
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Then configure API keys
```

### Data Ingestion
```bash
python -m src.ingest.ine          # INE population data
python -m src.ingest.turismo      # Tourism housing registry
python -m src.ingest.istac_data   # ISTAC statistics
python -m src.ingest.airbnb_data  # Airbnb data
```

### RAG Pipeline
```bash
python -m src.rag.pipeline        # Full indexing pipeline
```

### Run Server
```bash
# API
uvicorn src.rag.api:app --reload --port 8000

# Frontend
cd src/frontend && python -m http.server 8080
```

### Development
```bash
pytest                              # Run tests
jupyter notebook                    # Data exploration
```

## Architecture

```
src/
├── config.py              # Environment + paths config
├── ingest/                # Data collection scripts
│   ├── ine.py             # INE population data
│   ├── turismo.py         # Tourism registry
│   ├── istac_data.py     # ISTAC statistics
│   └── airbnb_data.py    # Airbnb scraping
├── rag/                   # RAG pipeline
│   ├── api.py             # FastAPI endpoints
│   ├── pipeline.py       # Main indexing pipeline
│   ├── embedder.py       # sentence-transformers embeddings
│   ├── indexer.py        # Pinecone operations
│   ├── chat.py           # LLM question answering
│   └── real_chunks.py    # Chunk generation
└── frontend/
    └── index.html        # Leaflet.js map + chatbot UI

data/
├── raw/                  # Raw downloaded data
└── processed/            # Cleaned data
```

## Key Patterns

### RAG Pipeline Flow
1. `load_processed_data()` → Load INE + Turismo CSVs
2. `create_chunks()` → Generate text chunks per barrio
3. `generate_embeddings()` → Embed with sentence-transformers
4. `index_data()` → Upsert to Pinecone

### FastAPI Endpoints
- `GET /health` — Health check
- `GET /barrios` — List available neighborhoods
- `POST /query` — RAG query with sources
- `GET /map-data` — Aggregated data for map

### Chunk Structure
```python
{
    "id": "ine_vegueta",
    "text": "En el barrio de Vegueta, según datos del INE...",
    "metadata": {
        "source": "INE - Padrón de habitantes",
        "barrio": "Vegueta",
        "tipo": "poblacion",
        "ano_inicio": 2015,
        "ano_fin": 2024
    }
}
```

## Configuration

Required environment variables (`.env`):
- `GROQ_API_KEY` — Groq API for LLM chat (free)
- `PINECONE_API_KEY` — Pinecone vector DB
- `PINECONE_INDEX` — Index name (default: gc-housing)
- `INE_CODIGO_MUNICIPIO` — INE municipality code (default: 35020 = Las Palmas GC)

## Key Conventions

- **Python**: Variables in English, comments in Spanish
- **Embeddings**: sentence-transformers `all-MiniLM-L6-v2` (384 dimensions)
- **Vector DB**: Pinecone with metadata filtering by barrio
- **Frontend**: Vanilla JS with Leaflet.js + dark theme
- **Commits**: conventional commits (feat:, fix:, refactor:)
