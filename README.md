# Éxodo Vecinal

**El mapa de la turistificación en Las Palmas de Gran Canaria.** Chatbot con RAG + mapa interactivo para visualizar el impacto de las viviendas vacacionales en los barrios.

## Stack

- **Python 3.13** + FastAPI
- **Pinecone** (vector DB) + **sentence-transformers** (embeddings local)
- **Groq** (LLM) + **Leaflet.js** (mapa interactivo, frontend vanilla)

## Arquitectura

```
Frontend (mapa + chat) → FastAPI → Pinecone (RAG)
                               ↓
                         Groq LLM (chat)
                               ↓
               sentence-transformers (embeddings)
```

## Datos

| Fuente | Cobertura | Archivo |
|--------|-----------|---------|
| ISTAC | 75 meses (01/2019-03/2025), municipio LPGC | `data/raw/istac_viviendas_lpgc_pivot.csv` |
| Doorstep (Airbnb) | 9,400 coords isla completa | `data/raw/doorstep_coordinates.csv` |
| Registro Turismo GC | 5,144 vv, 90.7% con barrio asignado | `data/raw/turismo_lpgc_with_barrios.csv` |
| INE Padrón | ⚠️ Sintético (INE bloquea acceso automático) | `data/raw/ine_population_processed.csv` |

## Endpoints

- `GET /health` — Health check
- `GET /barrios` — Lista de barrios disponibles
- `POST /query` — RAG query (embed → Pinecone → Groq → respuesta)
- `GET /map-data` — Datos agregados: ISTAC, Airbnb coords, INE sintético
- `GET /turismo-points` — Puntos de viviendas turísticas con barrios
- `GET /barrios-polygons` — Polígonos GeoJSON de barrios con conteo de vv

## Setup

```bash
# 1. Crear venv e instalar
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configurar .env
cp .env.example .env
# Editar con: GROQ_API_KEY, PINECONE_API_KEY

# 3. Reindexar Pinecone (si cambiaron los datos)
python -m src.rag.pipeline

# 4. Arrancar
uvicorn src.rag.api:app --reload --port 8000
cd src/frontend && python -m http.server 8080
```

## Estado

| Componente | Estado |
|------------|--------|
| Pipeline RAG | ✅ 32 chunks indexados (ISTAC + barrios + Doorstep) |
| Geocoding barrios | ✅ 90.7% cobertura (4,665/5,144 vv) |
| Mapa interactivo | ✅ Heatmap + polígonos de barrios |
| Chat RAG | ✅ Funcional con Groq |

## Próximos pasos

1. **i18n** — Internacionalización (es/en)
2. **Despliegue OVH** — Producción en servidor OVH
3. **INE real** — Solicitar formalmente o buscar mirror en datos.gob.es
