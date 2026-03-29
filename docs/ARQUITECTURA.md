# GC Housing RAG - Arquitectura del Sistema

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GC Housing RAG                                    │
│                  Análisis de Turistificación en LPGC                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Flujo de Datos

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   DATOS      │     │  INGESTION   │     │  RAG PIPELINE │     │   FRONTEND  │
│   FUENTES    │────▶│   (Python)   │────▶│  (Pinecone)  │────▶│  (Leaflet)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘

     ISTAC              ine.py              embedder.py         index.html
     INE                istac_data.py       indexer.py          heatmap
     Turismo            turismo.py          real_chunks.js
     Airbnb              geocoder.py        chat.py             API
     OpenStreetMap       reverse_geocode.py chat.py            FastAPI
```

## Componentes

### 1. Ingestión de Datos (`src/ingest/`)

| Script | Función |
|--------|---------|
| `ine.py` | Descarga datos de población del INE por barrio |
| `istac_data.py` | Obtiene estadísticas de viviendas vacacionales |
| `turismo.py` | scrapea Registro Turismo de Canarias |
| `geocoder.py` | Convierte direcciones a coordenadas (Nominatim) |
| `reverse_geocode.py` | Asigna barrio según coordenadas (shapely) |
| `assign_barrios.py` | Pipeline completo de asignación |

### 2. RAG Pipeline (`src/rag/`)

```
create_chunks() → generate_embeddings() → index_data()
     ↓                    ↓                   ↓
real_chunks.py      embedder.py         indexer.py
   (texto)         (sentence-          (Pinecone)
                    transformers)
```

### 3. API (`src/rag/api.py`)

| Endpoint | Descripción |
|---------|-------------|
| `GET /query` | Consulta RAG con contexto |
| `GET /map-data` | Datos agregados para mapa |
| `GET /turismo-points` | Puntos de viviendas turísticas |
| `GET /barrios-polygons` | Polígonos de barrios |
| `GET /health` | Health check |

### 4. Frontend (`src/frontend/`)

- **Mapa**: Leaflet.js con CARTO dark tiles
- **Heatmap**: leaflet.heat para densidad
- **Barrios**: GeoJSON con choropleth
- **Chat**: Integración con RAG

## Fuentes de Datos

| Fuente | Tipo | Cobertura |
|--------|------|-----------|
| ISTAC | Oficial (meses) | Municipio LPGC |
| INE | Población | Barrios (sintético) |
| Registro Turismo | Oficial (viviendas) | 90.7% con barrio |
| Doorstep Analytics | Airbnb scrapeado | Isla completa |
| ArcGIS | Polígonos | 122 barrios |

## Mapa de Arendizaje de Datos

```
                    ┌─────────────────────────┐
                    │   Registro Turismo     │
                    │   (turismo_lpgc.csv)  │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │     Geocodificación     │
                    │   (geocoder.py)         │
                    │   Dirección → Lat/Lon   │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │   Reverse Geocoding    │
                    │ (reverse_geocode.py)   │
                    │   Lat/Lon → Barrio    │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Chunks RAG   │    │ Mapa Calor      │    │ Tabla Barrios   │
│ ( Pinecone ) │    │ ( Leaflet heat )│    │ ( Sidebar )    │
└───────────────┘    └─────────────────┘    └─────────────────┘
```

## Tecnologías

- **Backend**: FastAPI (Python 3.13)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **LLM**: MiniMax API + Groq Llama
- **Vector DB**: Pinecone
- **Mapa**: Leaflet.js + CARTO dark
- **Heatmap**: leaflet.heat

## Costes Estimados

| Servicio | Uso | Coste |
|----------|-----|-------|
| Pinecone | 32 vectores | ~$0 |
| MiniMax | Embeddings | ~$1/mes |
| Groq | Chat | ~$0 |
| Nominatim | Geocoding | Gratuito |
| OVH | Hosting | ~€5/mes |
