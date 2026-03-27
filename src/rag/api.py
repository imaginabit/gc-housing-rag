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

from ..config import DATA_RAW_DIR
from .embedder import embed_query
from .indexer import query_index
from .chat import ask_question, format_map_context

app = FastAPI(
    title="GC Housing RAG API",
    description="API para consultar datos de turistificación en LPGC",
    version="0.1.0"
)

# CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción restringir
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
    
    result = {
        "barrios": [],
        "has_data": False
    }
    
    if ine_path.exists():
        df_ine = pd.read_csv(ine_path)
        ine_barrios = df_ine["barrio"].dropna().unique().tolist()
        result["barrios"] = ine_barrios
        result["has_data"] = True
    else:
        result["barrios"] = [
            "Vegueta", "Triana", "Mesa y López", "Playa de las Canteras",
            "La Isleta", "San Juan", "San Nicolás", "Alameda", "Cono Sur",
            "Tamaraceite", "La Paterca", "Tenoya", "Buena Vista"
        ]
    
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
            filter_dict=filter_dict
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
        sources.append({
            "barrio": meta.get("barrio", ""),
            "source": meta.get("source", ""),
            "tipo": meta.get("tipo", ""),
            "score": round(r.get("score", 0), 3)
        })
    
    return QueryResponse(
        answer=answer,
        sources=sources,
        map_data=map_data
    )


@app.get("/map-data")
def get_map_data():
    """
    Devuelve datos agregados por barrio para el mapa.
    """
    ine_path = DATA_RAW_DIR / "ine_population_processed.csv"
    turismo_path = DATA_RAW_DIR / "turismo_viviendas.csv"
    
    result = {}
    
    # INE - población por barrio y año
    if ine_path.exists():
        df_ine = pd.read_csv(ine_path)
        pop_by_barrio = df_ine.groupby(["barrio", "ano"])["poblacion"].sum().reset_index()
        pop_pivot = pop_by_barrio.pivot(index="barrio", columns="ano", values="poblacion").to_dict()
        
        # Último año disponible
        latest_ano = max(df_ine["ano"].unique())
        latest_pop = df_ine[df_ine["ano"] == latest_ano].groupby("barrio")["poblacion"].sum().to_dict()
        
        # Primer año para comparar
        first_ano = min(df_ine["ano"].unique())
        first_pop = df_ine[df_ine["ano"] == first_ano].groupby("barrio")["poblacion"].sum().to_dict()
        
        result["poblacion"] = {
            "latest_year": int(latest_ano),
            "first_year": int(first_ano),
            "by_barrio": {
                b: {
                    "poblacion": int(latest_pop.get(b, 0)),
                    "poblacion_inicio": int(first_pop.get(b, 0)),
                    "cambio_pct": round(
                        ((latest_pop.get(b, 0) - first_pop.get(b, 0)) / first_pop.get(b, 0) * 100)
                        if first_pop.get(b, 0) > 0 else 0,
                        1
                    )
                }
                for b in latest_pop.keys()
            }
        }
    
    # Turismo - viviendas por barrio
    if turismo_path.exists():
        df_tur = pd.read_csv(turismo_path)
        
        tur_by_barrio = df_tur.groupby("barrio").agg(
            num_viviendas=("registro", "count"),
            plazas_totales=("plazas", "sum")
        ).to_dict("index")
        
        result["turismo"] = {
            "by_barrio": {
                b: {
                    "viviendas": tur_by_barrio[b]["num_viviendas"],
                    "plazas": int(tur_by_barrio[b]["plazas_totales"])
                }
                for b in tur_by_barrio
            }
        }
    
    return result
