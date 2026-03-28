# 🏘️ GC Housing RAG

**Chatbot con RAG + mapa interactivo** para visualizar el impacto de las viviendas vacacionales en los barrios de Las Palmas de Gran Canaria.

## Stack

- **Python 3.13** + FastAPI
- **Pinecone** (vector DB) + **sentence-transformers** (embeddings local)
- **Groq** (LLM gratis) + **MiniMax** (embeddings)
- **Leaflet.js** (mapa interactivo, frontend vanilla)

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
| Registro Turismo GC | 5,144 vv con coords, sin desglose barrio | `data/raw/turismo_lpgc_real.csv` |
| INE Padrón | ⚠️ Sintético (INE bloquea acceso automático) | `data/raw/ine_population_processed.csv` |

## Endpoints

- `GET /health` — Health check
- `GET /barrios` — Lista de barrios disponibles
- `POST /query` — RAG query (embed → Pinecone → Groq → respuesta)
- `GET /map-data` — Datos agregados: ISTAC, Airbnb coords, INE sintético

## Setup

```bash
# 1. Crear venv e instalar
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configurar .env
cp .env.example .env
# Editar con: GROQ_API_KEY, MINIMAX_API_KEY, PINECONE_API_KEY

# 3. Descargar datos (opcional, ya hay datos en data/raw/)
python -m src.ingest.istac_data

# 4. Reindexar Pinecone (si cambiaron los datos)
python -m src.rag.pipeline

# 5. Arrancar
uvicorn src.rag.api:app --reload --port 8000
cd src/frontend && python -m http.server 8080
```

## API Keys necesarias

- `GROQ_API_KEY` — Groq (gratis, para chat)
- `MINIMAX_API_KEY` — MiniMax (embeddings)
- `PINECONE_API_KEY` — Pinecone (vector DB)

## Estado

| Componente | Estado |
|------------|--------|
| Pipeline RAG | ✅ Funcional |
| Datos ISTAC reales | ✅ 75 meses indexados |
| Mapa Airbnb coords | ✅ 9,400 puntos disponibles |
| INE por barrio | ⚠️ Sintético |
| Frontend | ⚠️ Necesita actualizar para nuevos datos |

## Próximos pasos

1. **Mapa de calor Airbnb** — Renderizar 9,400 puntos de Doorstep en el mapa
2. **Reverse geocoding** — Asignar barrio a cada vv del Registro Turismo con coords
3. **Gráficos ISTAC** — Visualizar la serie de 75 meses (evolución temporal)
4. **INE real** — Solicitar formalmente o buscar mirror en datos.gob.es
