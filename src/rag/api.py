"""
Backend FastAPI para GC Housing RAG.

Expone endpoints para:
- GET /health — health check
- GET /barrios — lista de barrios con datos
- POST /query — hacer una pregunta al RAG
- GET /map-data — datos para el mapa
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np

from ..config import DATA_RAW_DIR, ALLOWED_ORIGINS, BARRIOS_LPGC
from .embedder import embed_query
from .indexer import query_index
from .chat import ask_question, format_map_context

app = FastAPI(
    title="GC Housing RAG API",
    description="API para consultar datos de turistificación en LPGC",
    version="0.1.0",
)

# CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "gc-housing-rag"}


@app.get("/barrios")
def get_barrios():
    """
    Devuelve lista de barrios con datos disponibles.
    """
    ine_path = DATA_RAW_DIR / "ine_population_processed.csv"
    turismo_path = DATA_RAW_DIR / "turismo_viviendas.csv"

    result = {"barrios": [], "has_data": False}

    if ine_path.exists():
        df_ine = pd.read_csv(ine_path)
        ine_barrios = df_ine["barrio"].dropna().unique().tolist()
        result["barrios"] = ine_barrios
        result["has_data"] = True
    else:
        result["barrios"] = BARRIOS_LPGC

    return result


class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5
    barrio: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    map_data: Dict[str, Any]


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """
    Procesa una pregunta del usuario usando RAG.
    """
    # 1. Generar embedding de la query
    query_embedding = embed_query(request.question)

    if not query_embedding:
        raise HTTPException(status_code=500, detail="Error generando embedding")

    # 2. Buscar en Pinecone
    filter_dict = {"barrio": request.barrio} if request.barrio else None

    try:
        results = query_index(
            query_embedding=query_embedding,
            top_k=request.top_k,
            filter_dict=filter_dict,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en Pinecone: {str(e)}")

    # 3. Generar respuesta con LLM
    try:
        answer = ask_question(request.question, results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en LLM: {str(e)}")

    # 4. Formatear datos para el mapa
    map_data = format_map_context(results)

    # 5. Extraer sources para mostrar
    sources = []
    for r in results:
        meta = r.get("metadata", {})
        sources.append(
            {
                "barrio": meta.get("barrio", ""),
                "source": meta.get("source", ""),
                "tipo": meta.get("tipo", ""),
                "score": round(r.get("score", 0), 3),
            }
        )

    return QueryResponse(answer=answer, sources=sources, map_data=map_data)


def _np_to_native(obj):
    """Convierte tipos numpy a Python nativos para serialización JSON."""
    if isinstance(obj, dict):
        return {k: _np_to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_np_to_native(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


@app.get("/map-data")
def get_map_data():
    """
    Devuelve datos agregados para el mapa.

    Usa datos reales del ISTAC (municipio LPGC) y Doorstep (coords Airbnb).
    El INE por barrio es sintético — avisar en la respuesta.
    """
    ine_path = DATA_RAW_DIR / "ine_population_processed.csv"
    istac_path = DATA_RAW_DIR / "istac_viviendas_lpgc_pivot.csv"
    doorstep_coords_path = DATA_RAW_DIR / "doorstep_coordinates.csv"

    result = {}

    # ---- ISTAC: datos reales a nivel municipio LPGC ----
    if istac_path.exists():
        df_istac = pd.read_csv(istac_path)
        df_istac["periodo_dt"] = pd.to_datetime(df_istac["periodo"], format="%m/%Y")
        df_istac = df_istac.sort_values("periodo_dt")
        latest = df_istac.iloc[-1]

        # Penúltimo mes para comparar
        year_ago_idx = max(0, len(df_istac) - 12)
        year_ago = df_istac.iloc[year_ago_idx]

        viv_now = int(latest["Viviendas vacacionales disponibles"])
        viv_then = int(year_ago["Viviendas vacacionales disponibles"])
        plazas_now = int(latest["Plazas disponibles"])
        plazas_then = int(year_ago["Plazas disponibles"])

        result["istac"] = _np_to_native(
            {
                "periodo": latest["periodo"],
                "periodo_year_ago": year_ago["periodo"],
                "viviendas_disponibles": viv_now,
                "viviendas_change_pct": round((viv_now - viv_then) / viv_then * 100, 1)
                if viv_then > 0
                else 0,
                "plazas_disponibles": plazas_now,
                "plazas_change_pct": round(
                    (plazas_now - plazas_then) / plazas_then * 100, 1
                )
                if plazas_then > 0
                else 0,
                "tasa_ocupacion": round(float(latest["Tasa de vivienda reservada"]), 1),
                "estancia_media": round(
                    float(latest["Estancia media en la vivienda vacacional"]), 2
                ),
                "ingresos_totales": round(float(latest["Ingresos totales"]), 2),
                "viviendas_reservadas": int(
                    latest["Viviendas vacacionales reservadas"]
                ),
                "series": df_istac[
                    [
                        "periodo",
                        "Viviendas vacacionales disponibles",
                        "Plazas disponibles",
                        "Tasa de vivienda reservada",
                        "Estancia media en la vivienda vacacional",
                        "Ingresos totales",
                    ]
                ].to_dict(orient="records"),
            }
        )

    # ---- INE: población por barrio (SINTÉTICO — avisar) ----
    result["ine_synthetic"] = True
    if ine_path.exists():
        df_ine = pd.read_csv(ine_path)
        latest_ano = int(df_ine["ano"].max())
        first_ano = int(df_ine["ano"].min())
        latest_pop = (
            df_ine[df_ine["ano"] == latest_ano].groupby("barrio")["poblacion"].sum()
        )
        first_pop = (
            df_ine[df_ine["ano"] == first_ano].groupby("barrio")["poblacion"].sum()
        )

        by_barrio = {}
        for barrio in latest_pop.index:
            p_now = int(latest_pop.get(barrio, 0))
            p_then = int(first_pop.get(barrio, 0))
            cambio = round((p_now - p_then) / p_then * 100, 1) if p_then > 0 else 0
            by_barrio[barrio] = {
                "poblacion": p_now,
                "poblacion_inicio": p_then,
                "cambio_pct": cambio,
            }

        result["poblacion"] = {
            "latest_year": latest_ano,
            "first_year": first_ano,
            "is_synthetic": True,
            "by_barrio": by_barrio,
        }

    # ---- Doorstep: coordenadas Airbnb (isla completa) ----
    result["airbnb_coords"] = {"source": "Doorstep Analytics", "island": "Gran Canaria"}
    if doorstep_coords_path.exists():
        df_coords = pd.read_csv(doorstep_coords_path)
        # sample up to 5000 points for map performance
        if len(df_coords) > 5000:
            df_coords = df_coords.sample(5000, random_state=42)
        result["airbnb_coords"]["count"] = len(df_coords)
        result["airbnb_coords"]["points"] = _np_to_native(
            df_coords[["lat", "lng"]]
            .rename(columns={"lat": "lat", "lng": "lng"})
            .to_dict(orient="records")
        )

    return result
