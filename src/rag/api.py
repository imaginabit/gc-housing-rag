"""
Backend FastAPI para Éxodo Vecinal.

Expone endpoints para:
- GET /health — health check (verifica conexiones)
- GET /barrios — lista de barrios con datos
- POST /query — hacer una pregunta al RAG
- GET /map-data — datos agregados para el mapa
- GET /turismo-points — puntos de viviendas turísticas
- GET /barrios-polygons — polígonos GeoJSON de barrios
- GET /news — artículos curados sobre vivienda vacacional
- GET /* — frontend estático (catch-all)
"""

import logging

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
import json
import pandas as pd
import numpy as np
from pathlib import Path

from ..config import DATA_RAW_DIR, ALLOWED_ORIGINS, BARRIOS_LPGC
from .embedder import embed_query, check_embedding_dim
from .indexer import query_index
from .chat import ask_question, format_map_context

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Éxodo Vecinal API",
    description="API para consultar datos de turistificación en Las Palmas de Gran Canaria",
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

# Frontend estático (servido por uvicorn en producción)
_FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# Constants
MAX_QUESTION_LENGTH = 2000
MAX_TOP_K = 50


@app.get("/health")
def health():
    """
    Health check con verificación de dependencias.
    """
    checks = {}

    # Check embedding model
    try:
        test_emb = embed_query("test")
        checks["embedder"] = "ok" if test_emb and len(test_emb) == 384 else "error"
    except Exception as e:
        checks["embedder"] = f"error: {str(e)}"

    # Check Pinecone
    try:
        from .indexer import get_pinecone_client

        pc = get_pinecone_client()
        indexes = pc.list_indexes().names()
        checks["pinecone"] = "ok" if indexes is not None else "error"
    except Exception as e:
        checks["pinecone"] = f"error: {str(e)}"

    # Check data files
    data_files = ["barrios_lpgc.json", "turismo_lpgc_with_barrios.csv"]
    checks["data"] = {f: (DATA_RAW_DIR / f).exists() for f in data_files}

    all_ok = all(
        v == "ok" for k, v in checks.items() if k != "data" and isinstance(v, str)
    )

    return {
        "status": "ok" if all_ok else "degraded",
        "service": "gc-housing-rag",
        "checks": checks,
    }


@app.get("/barrios")
def get_barrios():
    """
    Devuelve lista de barrios con datos disponibles.
    """
    ine_path = DATA_RAW_DIR / "ine_population_processed.csv"

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

    @field_validator("question")
    @classmethod
    def question_must_be_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La pregunta no puede estar vacía")
        if len(v) > MAX_QUESTION_LENGTH:
            raise ValueError(
                f"La pregunta no puede exceder {MAX_QUESTION_LENGTH} caracteres"
            )
        return v

    @field_validator("top_k")
    @classmethod
    def top_k_must_be_reasonable(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > MAX_TOP_K):
            raise ValueError(f"top_k debe estar entre 1 y {MAX_TOP_K}")
        return v


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    map_data: Dict[str, Any]


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """
    Procesa una pregunta del usuario usando RAG.
    """
    logger.info(
        "Query: %s (top_k=%d, barrio=%s)",
        request.question[:100],
        request.top_k,
        request.barrio,
    )

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
        logger.error("Error en Pinecone: %s", e)
        raise HTTPException(status_code=500, detail=f"Error en Pinecone: {str(e)}")

    # 3. Generar respuesta con LLM
    try:
        answer = ask_question(request.question, results)
    except Exception as e:
        logger.error("Error en LLM: %s", e)
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

    logger.info(
        "Query completada: %d results, answer len=%d", len(results), len(answer)
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


def _normalize_barrio(name: str) -> str:
    """Normaliza nombre de barrio para matching: uppercase y strip."""
    return name.strip().upper()


def _calculate_barrio_ratios(
    vv_count: int, plazas: int, poblacion: int, viv_estimadas: float | None = None
) -> dict:
    """
    Calcula ratios de presión turística por barrio.

    Args:
        vv_count: número de viviendas vacacionales
        plazas: plazas totales
        poblacion: población del barrio
        viv_estimadas: viviendas estimadas (default: población / 2.2)

    Nota sobre viviendas estimadas:
        El INE no publica datos de viviendas por barrio para LPGC.
        Usamos población / tamaño_medio_hogar como proxy.
        2.2 = promedio Canarias (INE Censo 2021: 175181 viviendas / ~380k pop).
        Este cálculo es una estimación — no es un dato censal directo.

    Returns:
        Dict con ratios calculados. Poblacion 0 o negativas devuelven 0 en ratios.
    """
    if viv_estimadas is None:
        viv_estimadas = poblacion / 2.2

    result = {
        "vv_count": vv_count,
        "plazas": plazas,
        "poblacion": poblacion,
        "viv_estimadas": round(viv_estimadas, 1),
        "is_synthetic_population": True,
        "is_synthetic_viviendas": True,
    }

    if poblacion > 0:
        result["vv_per_1000hab"] = round((vv_count / poblacion) * 1000, 2)
        result["plazas_per_1000hab"] = round((plazas / poblacion) * 1000, 2)
    else:
        result["vv_per_1000hab"] = 0
        result["plazas_per_1000hab"] = 0

    if viv_estimadas > 0:
        result["vv_per_100_viviendas"] = round((vv_count / viv_estimadas) * 100, 2)
    else:
        result["vv_per_100_viviendas"] = 0

    return result


@app.get("/barrio-detail/{nombre}")
def get_barrio_detail(nombre: str):
    """
    Devuelve detalle completo de un barrio: VV, plazas, ratios, ranking.

    Usa datos del Registro Turismo (real) y población INE (sintética).
    """
    turismo_path = DATA_RAW_DIR / "turismo_lpgc_with_barrios.csv"
    ine_path = DATA_RAW_DIR / "ine_population_processed.csv"

    barrio_norm = _normalize_barrio(nombre)

    # ---- Turismo: datos reales por barrio ----
    vv_count = 0
    plazas_totales = 0
    vv_list = []

    if turismo_path.exists():
        df_tur = pd.read_csv(turismo_path)
        df_barrio = df_tur[df_tur["barrio_asignado"].notna()]
        df_barrio = df_barrio[df_barrio["barrio_asignado"] != "_U"]
        df_barrio = df_barrio[
            df_barrio["barrio_asignado"].apply(_normalize_barrio) == barrio_norm
        ]

        vv_count = len(df_barrio)
        plazas_totales = int(df_barrio["plazas"].fillna(0).sum())

        # Sample points para el mapa (máx 200)
        sample = df_barrio[df_barrio["lat"] != 0].head(200)
        vv_list = _np_to_native(
            sample[["lat", "lng", "plazas", "nombre"]]
            .fillna("")
            .to_dict(orient="records")
        )

    # ---- Población INE (sintética) ----
    poblacion = 0
    if ine_path.exists():
        df_ine = pd.read_csv(ine_path)
        latest_ano = int(df_ine["ano"].max())
        row = df_ine[
            (df_ine["ano"] == latest_ano)
            & (df_ine["barrio"].apply(_normalize_barrio) == barrio_norm)
        ]
        if not row.empty:
            poblacion = int(row["poblacion"].iloc[0])

    # Si no hay datos, devolver 404
    if vv_count == 0 and poblacion == 0:
        raise HTTPException(status_code=404, detail=f"Barrio '{nombre}' no encontrado")

    ratios = _calculate_barrio_ratios(vv_count, plazas_totales, poblacion)

    # ---- Ranking: posición del barrio en el top total ----
    ranking = None
    if turismo_path.exists():
        df_tur = pd.read_csv(turismo_path)
        df_all = df_tur[df_tur["barrio_asignado"].notna()]
        df_all = df_all[df_all["barrio_asignado"] != "_U"]
        counts = df_all.groupby(
            df_all["barrio_asignado"].apply(_normalize_barrio)
        ).size()
        counts = counts.sort_values(ascending=False)
        if barrio_norm in counts.index:
            posicion = counts.index.get_loc(barrio_norm) + 1
            ranking = {
                "posicion": posicion,
                "total_barrios_con_vv": len(counts),
                "vv_en_posicion": int(counts.iloc[posicion - 1]),
            }

    # Ratios municipales de referencia (INE Censo 2021 + Registro Turismo total)
    VIVIENDAS_MUNICIPIO_CENSO_2021 = 175181
    VV_TOTAL_MUNICIPIO = 4531  # Total VV del Registro Turismo para LPGC
    vv_per_100_viviendas_municipal = round(
        VV_TOTAL_MUNICIPIO / VIVIENDAS_MUNICIPIO_CENSO_2021 * 100, 2
    )

    return _np_to_native(
        {
            "barrio": nombre.strip(),
            "barrio_normalized": barrio_norm,
            "viviendas_count": vv_count,
            "plazas": plazas_totales,
            "poblacion": poblacion,
            "ratios": ratios,
            "ranking": ranking,
            "points": vv_list,
            "vv_per_100_viviendas_municipal": vv_per_100_viviendas_municipal,
            "sources": {
                "viviendas": "Registro Turismo de Canarias",
                "poblacion": "INE (sintético — ekstracción por ekstracción de la población)",
                "viviendas_municipio": "INE Censo 2021 (tabla 59525) — 175,181 viviendas",
            },
        }
    )

    return _np_to_native(
        {
            "barrio": nombre.strip(),
            "barrio_normalized": barrio_norm,
            "viviendas_count": vv_count,
            "plazas": plazas_totales,
            "poblacion": poblacion,
            "ratios": ratios,
            "ranking": ranking,
            "points": vv_list,
            "vv_per_100_viviendas_municipal": vv_per_100_viviendas_municipal,
            "sources": {
                "viviendas": "Registro Turismo de Canarias",
                "poblacion": "INE (sintético — ekstracción por ekstracción de la población)",
                "viviendas_municipio": "INE Censo 2021 (tabla 59525) — 175,181 viviendas",
            },
        }
    )


@app.get("/stats-overview")
def get_stats_overview(top_n: int = 15):
    """
    Overview de estadísticas: top barrios, totales, comparativa YoY.

    Args:
        top_n: número de barrios en el ranking (default 15, max 50)
    """
    top_n = max(1, min(50, top_n))

    turismo_path = DATA_RAW_DIR / "turismo_lpgc_with_barrios.csv"
    ine_path = DATA_RAW_DIR / "ine_population_processed.csv"
    istac_path = DATA_RAW_DIR / "istac_viviendas_lpgc_pivot.csv"

    result = {
        "top_barrios": [],
        "totales": {},
        "yoy_istac": None,
    }

    # ---- Top barrios por VV count ----
    if turismo_path.exists():
        df_tur = pd.read_csv(turismo_path)
        df_valid = df_tur[df_tur["barrio_asignado"].notna()]
        df_valid = df_valid[df_valid["barrio_asignado"] != "_U"]

        # Agrupar por barrio normalizado
        grouped = (
            df_valid.groupby(df_valid["barrio_asignado"].apply(_normalize_barrio))
            .agg(
                vv_count=("establecimiento_id", "count"),
                plazas=("plazas", "sum"),
            )
            .reset_index()
        )
        # Filtrar: excluir el nombre del municipio (no es un barrio real)
        grouped = grouped[grouped["barrio_asignado"] != "LAS PALMAS DE GRAN CANARIA"]
        grouped = grouped.sort_values("vv_count", ascending=False).head(top_n)

        top_barrios = []
        for _, row in grouped.iterrows():
            barrio_norm = row["barrio_asignado"]
            # Buscar población para ese barrio
            poblacion = 0
            if ine_path.exists():
                df_ine = pd.read_csv(ine_path)
                latest_ano = int(df_ine["ano"].max())
                ine_row = df_ine[
                    (df_ine["ano"] == latest_ano)
                    & (df_ine["barrio"].apply(_normalize_barrio) == barrio_norm)
                ]
                if not ine_row.empty:
                    poblacion = int(ine_row["poblacion"].iloc[0])

            ratios = _calculate_barrio_ratios(
                int(row["vv_count"]), int(row["plazas"]), poblacion
            )
            top_barrios.append(
                {
                    "barrio": barrio_norm,
                    "vv_count": int(row["vv_count"]),
                    "plazas": int(row["plazas"]),
                    "ratios": ratios,
                }
            )

        result["top_barrios"] = _np_to_native(top_barrios)

        # ---- Totales municipio + ratio real con censo 2021 ----
        vv_total = int(df_valid["establecimiento_id"].count())
        plazas_total = int(df_valid["plazas"].fillna(0).sum())
        # INE Censo 2021: 175181 viviendas familiares en LPGC (35016)
        # Fuente: https://ine.es/dynt3/inebase/es/index.htm?padre=8952&capsel=9809 (tabla 59525)
        VIVIENDAS_MUNICIPIO_CENSO_2021 = 175181
        POBLACION_MUNICIPIO_INE_2024 = 380436

        result["totales"] = _np_to_native(
            {
                "vv_total": vv_total,
                "plazas_total": plazas_total,
                "barrios_con_vv": int(grouped["barrio_asignado"].nunique()),
                "barrios_analizados": top_n,
                # Ratios municipales con datos reales del Censo 2021
                "viviendas_municipio_censo_2021": VIVIENDAS_MUNICIPIO_CENSO_2021,
                "poblacion_municipio_ine_2024": POBLACION_MUNICIPIO_INE_2024,
                "vv_per_100_viviendas_municipal": round(
                    vv_total / VIVIENDAS_MUNICIPIO_CENSO_2021 * 100, 2
                ),
            }
        )

    # ---- Comparativa YoY desde ISTAC ----
    if istac_path.exists():
        df_istac = pd.read_csv(istac_path)
        df_istac["periodo_dt"] = pd.to_datetime(df_istac["periodo"], format="%m/%Y")
        df_istac = df_istac.sort_values("periodo_dt")

        latest = df_istac.iloc[-1]
        year_ago_idx = max(0, len(df_istac) - 12)
        year_ago = df_istac.iloc[year_ago_idx]

        result["yoy_istac"] = _np_to_native(
            {
                "periodo_actual": latest["periodo"],
                "periodo_year_ago": year_ago["periodo"],
                "vv_actual": int(latest["Viviendas vacacionales disponibles"]),
                "vv_year_ago": int(year_ago["Viviendas vacacionales disponibles"]),
                "vv_change_pct": round(
                    (
                        int(latest["Viviendas vacacionales disponibles"])
                        - int(year_ago["Viviendas vacacionales disponibles"])
                    )
                    / int(year_ago["Viviendas vacacionales disponibles"])
                    * 100,
                    1,
                )
                if int(year_ago["Viviendas vacacionales disponibles"]) > 0
                else 0,
                "series": _np_to_native(
                    df_istac[
                        [
                            "periodo",
                            "Viviendas vacacionales disponibles",
                            "Plazas disponibles",
                        ]
                    ].to_dict(orient="records")
                ),
            }
        )

    return result


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

    # ---- Ratios VV/población por barrio ----
    result["ratios"] = {"by_barrio": {}}
    turismo_path = DATA_RAW_DIR / "turismo_lpgc_with_barrios.csv"
    if turismo_path.exists() and ine_path.exists():
        df_tur = pd.read_csv(turismo_path)
        df_valid = df_tur[df_tur["barrio_asignado"].notna()]
        df_valid = df_valid[df_valid["barrio_asignado"] != "_U"]

        grouped = df_valid.groupby(
            df_valid["barrio_asignado"].apply(_normalize_barrio)
        ).agg(vv_count=("establecimiento_id", "count"), plazas=("plazas", "sum"))

        df_ine = pd.read_csv(ine_path)
        latest_ano = int(df_ine["ano"].max())
        df_ine_latest = df_ine[df_ine["ano"] == latest_ano].copy()
        df_ine_latest["barrio_norm"] = df_ine_latest["barrio"].apply(_normalize_barrio)
        latest_pop = df_ine_latest.set_index("barrio_norm")["poblacion"]

        ratios_by_barrio = {}
        for barrio_norm, row in grouped.iterrows():
            poblacion = int(latest_pop.get(barrio_norm, 0))
            ratios = _calculate_barrio_ratios(
                int(row["vv_count"]), int(row["plazas"]), poblacion
            )
            ratios_by_barrio[barrio_norm] = ratios

        result["ratios"]["by_barrio"] = _np_to_native(ratios_by_barrio)

    return result


@app.get("/turismo-points")
def get_turismo_points():
    """Devuelve puntos de viviendas turísticas del Registro Turismo."""
    turismo_path = DATA_RAW_DIR / "turismo_lpgc_with_barrios.csv"

    if not turismo_path.exists():
        return {"error": "Datos no disponibles", "points": []}

    df = pd.read_csv(turismo_path)
    valid = df[(df["lat"] != 0) & (df["lng"] != 0)]

    if len(valid) > 5000:
        valid = valid.sample(5000, random_state=42)

    # Fill NaN values before converting to dict
    valid = valid.fillna("")
    points = valid[["lat", "lng", "barrio_asignado", "plazas"]].to_dict(
        orient="records"
    )

    return {
        "source": "Registro Turismo de Canarias",
        "total": len(df),
        "with_coords": len(valid),
        "coverage_pct": round(len(valid) / len(df) * 100, 1),
        "points": points,
    }


@app.get("/barrios-polygons")
def get_barrios_polygons(response: Response):
    """Devuelve polígonos de barrios de LPGC con datos de viviendas."""
    barrios_path = DATA_RAW_DIR / "barrios_lpgc.json"
    turismo_path = DATA_RAW_DIR / "turismo_lpgc_with_barrios.csv"

    if not barrios_path.exists():
        return {
            "error": "Polígonos no disponibles",
            "type": "FeatureCollection",
            "features": [],
        }

    # Load tourism data for counts
    counts = {}
    if turismo_path.exists():
        df = pd.read_csv(turismo_path)
        df = df[df["barrio_asignado"].notna() & (df["barrio_asignado"] != "_U")]
        counts = df["barrio_asignado"].value_counts().to_dict()

    with open(barrios_path, encoding="utf-8") as f:
        data = json.load(f)

    # Filter out diseminado and add counts
    features = []
    for feat in data.get("features", []):
        nombre = feat.get("properties", {}).get("NUCL_DS_NOMBRE", "")
        # Skip diseminado
        if "DISEMINADO" in nombre.upper():
            continue
        # Add count
        count = counts.get(nombre.upper(), 0)
        feat["properties"]["viviendas_count"] = count
        features.append(feat)

    result = {
        "type": "FeatureCollection",
        "features": features,
    }

    return result


# Noticias: lee de data/raw/news_articles.json (generado por news_scraper)
# Fallback: artículos curados manualmente
_NEWS_FILE = DATA_RAW_DIR / "news_articles.json"

_FALLBACK_ARTICLES = [
    {
        "title": "Las Palmas de Gran Canaria abandona la carrera del crecimiento turístico tras un año con récord de visitantes",
        "source": "Canarias7",
        "url": "https://www.canarias7.es/canarias/gran-canaria/las-palmas-de-gran-canaria/palmas-gran-canaria-abandona-carrera-crecimiento-turistico-20260211071500-nt.html",
        "date": "2026-02-11",
        "topic": "legislación",
    },
    {
        "title": "Vecinos de El Médano alertan de que hay 3 veces más viviendas vacacionales de las registradas",
        "source": "Diario de Avisos",
        "url": "https://diariodeavisos.elespanol.com/2026/01/viviendas-vacacionales-el-medano/",
        "date": "2026-01-26",
        "topic": "denuncia vecinal",
    },
    {
        "title": "Foro Isleta: 'La vivienda vacacional rompe a las familias y genera un éxodo de vecinos'",
        "source": "COPE",
        "url": "https://www.cope.es/emisoras/canarias/las-palmas/gran-canaria/noticias/foro-isleta-vivienda-vacacional-rompe-las-familias-genera-exodo-vecinos-20240401_3223529",
        "date": "2024-04-01",
        "topic": "denuncia vecinal",
    },
]


def _load_news() -> list[dict]:
    """Carga artículos del scraper, con fallback a artículos curados."""
    if _NEWS_FILE.exists():
        try:
            with open(_NEWS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            articles = data.get("articles", [])
            if articles:
                return articles
        except Exception as e:
            logger.warning(f"Error leyendo news_articles.json: {e}")
    return _FALLBACK_ARTICLES


@app.get("/news")
def get_news():
    """Devuelve artículos recientes sobre vivienda vacacional en Canarias."""
    articles = _load_news()
    return {
        "source": "Éxodo Vecinal — curación de noticias",
        "total": len(articles),
        "articles": articles[:30],
    }


# Frontend: servir index.html para cualquier ruta que no sea API
@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    """Sirve el frontend estático para cualquier ruta no-API."""
    # Si piden un archivo específico que existe, servirlo
    file_path = _FRONTEND_DIR / full_path
    if full_path and file_path.is_file():
        return FileResponse(file_path)
    # Siempre servir index.html (SPA behavior)
    return FileResponse(_FRONTEND_DIR / "index.html")
