# 🏘️ GC Housing RAG — Mapa del Problema de la Turistificación en Las Palmas GC

Chatbot con RAG + mapa interactivo para visualizar el impacto de las viviendas vacacionales en los barrios de Las Palmas de Gran Canaria.

## Idea

Un mapa interactivo donde puedes ver barrio por barrio:
- 📉 Evolución de población (INE, 2015-2024)
- 🏠 Pisos turísticos registrados (Registro Turismo GC)
- 📰 Contexto: noticias y reportes sobre turistificación

Y un chatbot que responde preguntas como:
> "¿Qué barrios de Vegueta han perdido más vecinos?"
> "¿Cuántos pisos turísticos hay en Playa de las Canteras comparado con 2020?"

## Stack

- **LLM + Embeddings**: MiniMax API
- **Vector DB**: Pinecone (free tier)
- **Mapa**: Leaflet.js + OpenStreetMap
- **Backend**: FastAPI
- **Frontend**: HTML + vanilla JS

## Estructura

```
gc-housing-rag/
├── data/               # Datos crudos y procesados
├── src/
│   ├── ingest/         # Scripts de ingestión de datos
│   ├── rag/            # Pipeline RAG
│   └── frontend/       # Webapp
├── notebooks/          # Jupyter para experimentación
├── docs/               # Documentación
└── ...
```

## Setup

```bash
# 1. Clonar y entrar
cd ~/projects/gc-housing-rag

# 2. Crear virtualenv
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus claves de API

# 5. Ingesta de datos (una vez)
python -m src.ingest.ine     # Descargar INE
python -m src.ingest.turismo  # Descargar registro turismo

# 6. Indexar en Pinecone
python -m src.rag.index

# 7. Arrancar
cd src/frontend
python -m http.server 8080
```

## API Keys necesarias

- `MINIMAX_API_KEY` — API de MiniMax ( embeddings + chat)
- `MINIMAX_BASE_URL` — Base URL de MiniMax (para tu plan)
- `PINECONE_API_KEY` — API de Pinecone
- `PINECONE_INDEX` — Nombre del índice (default: `gc-housing`)

## Licencia

MIT — Libre para usar y modificar.
