"""
Chunks de datos reales para el RAG.

Usa datos reales del ISTAC (Instituto Canario de Estadística) y Doorstep Analytics.
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from ..config import DATA_RAW_DIR


def load_real_data() -> Dict[str, pd.DataFrame]:
    """Carga los datos reales disponibles."""
    data = {}

    # ISTAC - datos reales de viviendas vacacionales LPGC (municipio)
    istac_path = DATA_RAW_DIR / "istac_viviendas_lpgc_pivot.csv"
    if istac_path.exists():
        data["istac"] = pd.read_csv(istac_path)
        data["istac"]["periodo_dt"] = pd.to_datetime(
            data["istac"]["periodo"], format="%m/%Y"
        )
        data["istac"] = data["istac"].sort_values("periodo_dt")
        print(f"  ✅ ISTAC: {len(data['istac'])} meses de datos (LPGC municipio)")

    # Doorstep - stats Airbnb Gran Canaria
    doorstep_path = DATA_RAW_DIR / "doorstep_stats.csv"
    if doorstep_path.exists():
        data["doorstep_stats"] = pd.read_csv(doorstep_path)
        print(f"  ✅ Doorstep stats: {len(data['doorstep_stats'])} registros")

    # Doorstep - coordenadas Airbnb
    doorstep_coords = DATA_RAW_DIR / "doorstep_coordinates.csv"
    if doorstep_coords.exists():
        data["doorstep_coords"] = pd.read_csv(doorstep_coords)
        print(f"  ✅ Doorstep coords: {len(data['doorstep_coords'])} puntos")

    # INE sintético (solo para barrios donde no hay real)
    ine_path = DATA_RAW_DIR / "ine_population_processed.csv"
    if ine_path.exists():
        data["ine"] = pd.read_csv(ine_path)
        print(f"  ⚠️  INE: {len(data['ine'])} registros (SINTÉTICO - no real)")

    # Registro Turismo Canarias (sin desglose barrio)
    turismo_path = DATA_RAW_DIR / "turismo_lpgc_real.csv"
    if turismo_path.exists():
        data["turismo"] = pd.read_csv(turismo_path)
        print(f"  ⚠️  Registro Turismo: {len(data['turismo'])} vv (sin desglose barrio)")

    # Turismo con barrios asignados (nuevo - desde reverse geocoding)
    turismo_barrios_path = DATA_RAW_DIR / "turismo_lpgc_with_barrios.csv"
    if turismo_barrios_path.exists():
        data["turismo_barrios"] = pd.read_csv(turismo_barrios_path)
        # Contar coverage
        with_barrio = data["turismo_barrios"]["barrio_asignado"].notna().sum()
        print(f"  ✅ Turismo con barrios: {len(data['turismo_barrios'])} vv ({with_barrio} con barrio)")

    return data


def create_istac_chunks(istac: pd.DataFrame) -> List[Dict[str, Any]]:
    """Crea chunks con datos reales del ISTAC."""
    chunks = []

    # Evolución temporal LPGC
    if not istac.empty:
        # Último año completo
        latest = istac[istac["periodo_dt"] == istac["periodo_dt"].max()].iloc[0]
        year_ago = istac[
            istac["periodo_dt"] <= latest["periodo_dt"] - pd.DateOffset(months=11)
        ]
        year_ago = year_ago.iloc[0] if not year_ago.empty else latest

        # Crecimiento anual
        viv_change = (
            (
                (
                    latest["Viviendas vacacionales disponibles"]
                    - year_ago["Viviendas vacacionales disponibles"]
                )
                / year_ago["Viviendas vacacionales disponibles"]
                * 100
            )
            if year_ago["Viviendas vacacionales disponibles"] > 0
            else 0
        )
        plazas_change = (
            (
                (latest["Plazas disponibles"] - year_ago["Plazas disponibles"])
                / year_ago["Plazas disponibles"]
                * 100
            )
            if year_ago["Plazas disponibles"] > 0
            else 0
        )

        # Temporada alta vs baja (agosto vs febrero del último año)
        latest_year = istac[istac["periodo_dt"].dt.year == latest["periodo_dt"].year]
        aug = latest_year[latest_year["periodo"].str.startswith("08/")]
        feb = latest_year[latest_year["periodo"].str.startswith("02/")]
        alta = aug.iloc[0] if not aug.empty else None
        baja = feb.iloc[0] if not feb.empty else None

        # Chunk: evolución LPGC
        text = (
            f"En Las Palmas de Gran Canaria, según datos oficiales del ISTAC "
            f"(Instituto Canario de Estadística), hay {int(latest['Viviendas vacacionales disponibles']):,} "
            f"viviendas vacacionales disponibles en {latest['periodo']}. "
            f"En el último año (comparando {latest['periodo']} con {year_ago['periodo']}), "
            f"las viviendas han crecido un {viv_change:+.1f}% "
            f"y las plazas un {plazas_change:+.1f}%. "
            f"La tasa de ocupación es del {latest['Tasa de vivienda reservada']:.1f}%, "
            f"con una estancia media de {latest['Estancia media en la vivienda vacacional']:.1f} noches. "
            f"Los ingresos totales fueron {latest['Ingresos totales']:,.0f} €."
        )
        chunks.append(
            {
                "id": "istac_lpgc_evolucion",
                "text": text,
                "metadata": {
                    "source": "ISTAC - Instituto Canario de Estadística (datos oficiales)",
                    "barrio": "Las Palmas GC",
                    "tipo": "viviendas_vacacionales",
                    "viviendas_disponibles": int(
                        latest["Viviendas vacacionales disponibles"]
                    ),
                    "plazas_disponibles": int(latest["Plazas disponibles"]),
                    "tasa_ocupacion": round(latest["Tasa de vivienda reservada"], 1),
                    "estancia_media": round(
                        latest["Estancia media en la vivienda vacacional"], 2
                    ),
                    "ingresos_totales": round(latest["Ingresos totales"], 2),
                    "periodo": latest["periodo"],
                    "text": text,
                },
            }
        )

        # Chunk: crecimiento histórico
        first = istac.iloc[0]
        crecimiento_total_viv = (
            (
                (
                    latest["Viviendas vacacionales disponibles"]
                    - first["Viviendas vacacionales disponibles"]
                )
                / first["Viviendas vacacionales disponibles"]
                * 100
            )
            if first["Viviendas vacacionales disponibles"] > 0
            else 0
        )

        text2 = (
            f"Desde {first['periodo']} hasta {latest['periodo']}, "
            f"las viviendas vacacionales en Las Palmas de Gran Canaria han crecido "
            f"de {int(first['Viviendas vacacionales disponibles']):,} a {int(latest['Viviendas vacacionales disponibles']):,}, "
            f"un {crecimiento_total_viv:+.1f}% en el período. "
            f"En plazas disponibles, el crecimiento fue de "
            f"{int(first['Plazas disponibles']):,} a {int(latest['Plazas disponibles']):,}. "
            f"Esta tendencia refleja el auge del alquiler vacacional en la capital grancanaria."
        )
        chunks.append(
            {
                "id": "istac_lpgc_crecimiento",
                "text": text2,
                "metadata": {
                    "source": "ISTAC - Instituto Canario de Estadística",
                    "barrio": "Las Palmas GC",
                    "tipo": "crecimiento",
                    "periodo_inicio": first["periodo"],
                    "periodo_fin": latest["periodo"],
                    "text": text2,
                },
            }
        )

        # Chunk: estacionalidad (si hay datos)
        if alta and baja:
            text3 = (
                f"En Las Palmas de Gran Canaria, la estacionalidad del alquiler vacacional muestra "
                f"que en temporada alta (agosto) hay {int(alta['Viviendas vacacionales disponibles']):,} viviendas disponibles "
                f"con una tasa de ocupación del {alta['Tasa de vivienda reservada']:.1f}%, "
                f"mientras que en temporada baja (febrero) bajan a {int(baja['Viviendas vacacionales disponibles']):,} "
                f"con una ocupación del {baja['Tasa de vivienda reservada']:.1f}%. "
                f"La estancia media en agosto es de {alta['Estancia media en la vivienda vacacional']:.1f} noches "
                f"y en febrero de {baja['Estancia media en la vivienda vacacional']:.1f} noches."
            )
            chunks.append(
                {
                    "id": "istac_lpgc_estacionalidad",
                    "text": text3,
                    "metadata": {
                        "source": "ISTAC - Instituto Canario de Estadística",
                        "barrio": "Las Palmas GC",
                        "tipo": "estacionalidad",
                        "viviendas_alta": int(
                            alta["Viviendas vacacionales disponibles"]
                        )
                        if alta is not None
                        else None,
                        "viviendas_baja": int(
                            baja["Viviendas vacacionales disponibles"]
                        )
                        if baja is not None
                        else None,
                        "text": text3,
                    },
                }
            )

    return chunks


def create_doorstep_chunks(stats: pd.DataFrame) -> List[Dict[str, Any]]:
    """Crea chunks con datos de Doorstep Analytics (Airbnb Gran Canaria)."""
    chunks = []

    if stats.empty:
        return chunks

    row = stats.iloc[0]

    # Chunk: datos Airbnb Gran Canaria (isla completa)
    text = (
        f"Según Doorstep Analytics (datos de Airbnb scrapeados publicly, última actualización {row['last_updated']}), "
        f"hay {row['total_listings']:,} anuncios de Airbnb en Gran Canaria. "
        f"De estos, {row['entire_homes']:,} son viviendas completas (entire homes), "
        f"{row['private_rooms']:,} son habitaciones privadas, "
        f"{row['serviced_apartments']:,} son apartamentos turísticos, "
        f"y {row['shared_rooms']:,} son habitaciones compartidas. "
        f"Por número de dormitorios: {row['bed_1']:,} de 1 dormitorio, {row['bed_2']:,} de 2 dormitorios, "
        f"{row['bed_3']:,} de 3 dormitorios. "
        f"Notar que estos datos incluyen toda la isla de Gran Canaria, no solo Las Palmas de GC."
    )
    chunks.append(
        {
            "id": "doorstep_airbnb_grancanaria",
            "text": text,
            "metadata": {
                "source": "Doorstep Analytics (Airbnb data)",
                "barrio": "Gran Canaria (isla completa)",
                "tipo": "airbnb",
                "total_listings": int(row["total_listings"]),
                "entire_homes": int(row["entire_homes"]),
                "private_rooms": int(row["private_rooms"]),
                "last_updated": row["last_updated"],
                "text": text,
            },
        }
    )

    return chunks


def create_ratio_chunks(istac: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Crea chunks comparativos.
    NOTE: ISTAC solo tiene datos a nivel municipio LPGC, no por barrio.
    Los ratios de barrio usan datos sintéticos del INE para población.
    """
    chunks = []

    if istac.empty:
        return chunks

    # Para ratio necesitamos población por barrio (INE sintético)
    ine_path = DATA_RAW_DIR / "ine_population_processed.csv"
    if not ine_path.exists():
        return chunks

    ine = pd.read_csv(ine_path)

    # Solo podemos hacer ratio a nivel municipio LPGC
    latest = istac[istac["periodo_dt"] == istac["periodo_dt"].max()].iloc[0]

    # Población LPGC aprox (380,000)
    pob_lpgc = 380000  # estimación

    plazas = latest["Plazas disponibles"]
    ratio = plazas / pob_lpgc * 100

    text = (
        f"En Las Palmas de Gran Canaria (municipio), hay {int(plazas):,} plazas "
        f"en viviendas vacacionales (ISTAC) para una población aproximada de {pob_lpgc:,} habitantes. "
        f"El ratio es de {ratio:.1f} plazas turísticas por cada 100 habitantes. "
        f"Esto significa que por cada 100 residentes en LPGC, hay {ratio:.1f} plazas "
        f"destinadas al alquiler vacacional. "
        f"Un ratio alto indica mayor presión turística sobre el mercado de vivienda."
    )
    chunks.append(
        {
            "id": "ratio_lpgc_municipio",
            "text": text,
            "metadata": {
                "source": "Análisis comparativo ISTAC + estimación población",
                "barrio": "Las Palmas GC",
                "tipo": "ratio",
                "poblacion": pob_lpgc,
                "plazas_turisticas": int(plazas),
                "ratio_por_100": round(ratio, 1),
                "text": text,
            },
        }
    )

    return chunks


def create_context_chunk() -> List[Dict[str, Any]]:
    """Chunk de contexto general."""
    chunks = [
        {
            "id": "contexto_general",
            "text": (
                "Las Palmas de Gran Canaria es la capital de la isla de Gran Canaria, "
                "con aproximadamente 380,000 habitantes en el municipio. "
                "En los últimos años, el turismo de apartamentos y viviendas vacacionales ha crecido significativamente, "
                "especialmente en los barrios del centro histórico (Vegueta), Triana, "
                "y la franja costera de Playa de las Canteras. "
                "Según el ISTAC, en diciembre de 2024 hay 2,523 viviendas vacacionales disponibles "
                "con 8,972 plazas y una tasa de ocupación del 97.5%. "
                "Este crecimiento ha generado preocupación entre los vecinos por el aumento "
                "de los alquileres, la pérdida de residentes en barrios históricos, "
                "y el impacto en el comercio de proximidad."
            ),
            "metadata": {
                "source": "Contexto general",
                "barrio": "Las Palmas GC",
                "tipo": "contexto",
                "text": "Contexto general sobre LPGC",
            },
        }
    ]
    return chunks


def create_barrio_chunks(turismo_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Crea chunks con datos de viviendas por barrio."""
    chunks = []

    if "barrio_asignado" not in turismo_df.columns:
        return chunks

    # Agrupar por barrio
    grouped = turismo_df.groupby("barrio_asignado")

    for barrio, group in grouped:
        if pd.isna(barrio) or barrio == "_U":
            continue

        num_viviendas = len(group)
        plazas_total = group["plazas"].sum() if "plazas" in group.columns else 0

        # Solo crear chunk si hay suficientes viviendas
        if num_viviendas < 5:
            continue

        plazas_avg = plazas_total / num_viviendas if num_viviendas > 0 else 0

        # Chunk por barrio
        text = (
            f"En el barrio de {barrio}, según el Registro de Turismo de Canarias, "
            f"hay {num_viviendas:,} viviendas vacacionales registradas "
            f"con un total de {int(plazas_total):,} plazas. "
            f"Este barrio forma parte de Las Palmas de Gran Canaria y ha experimentado "
            f"un crecimiento significativo en el sector del alquiler vacacional."
        )

        chunks.append(
            {
                "id": f"turismo_{barrio.lower().replace(' ', '_').replace('-', '_')}",
                "text": text,
                "metadata": {
                    "source": "Registro Turismo Canarias (datos con barrios)",
                    "barrio": barrio,
                    "tipo": "viviendas_por_barrio",
                    "num_viviendas": int(num_viviendas),
                    "plazas_totales": int(plazas_total),
                    "plazas_promedio": round(plazas_avg, 1),
                    "text": text,
                },
            }
        )

    return chunks


def create_all_chunks() -> List[Dict[str, Any]]:
    """Crea todos los chunks para indexar."""
    print("\n📝 Creando chunks con datos reales...")
    data = load_real_data()

    all_chunks = []

    # ISTAC chunks
    if "istac" in data:
        chunks = create_istac_chunks(data["istac"])
        all_chunks.extend(chunks)
        print(f"  ISTAC: {len(chunks)} chunks")

    # Doorstep chunks
    if "doorstep_stats" in data:
        chunks = create_doorstep_chunks(data["doorstep_stats"])
        all_chunks.extend(chunks)
        print(f"  Doorstep: {len(chunks)} chunks")

    # Ratio chunks
    if "istac" in data:
        chunks = create_ratio_chunks(data["istac"])
        all_chunks.extend(chunks)
        print(f"  Ratios: {len(chunks)} chunks")

    # Contexto
    chunks = create_context_chunk()
    all_chunks.extend(chunks)
    print(f"  Contexto: {len(chunks)} chunks")

    #Chunks por barrio (desde reverse geocoding)
    if "turismo_barrios" in data:
        chunks = create_barrio_chunks(data["turismo_barrios"])
        all_chunks.extend(chunks)
        print(f"  Barrios: {len(chunks)} chunks")

    print(f"\n  ✅ Total: {len(all_chunks)} chunks")
    return all_chunks


if __name__ == "__main__":
    chunks = create_all_chunks()
    for c in chunks:
        print(f"\n[{c['id']}]")
        print(f"  {c['text'][:200]}...")
