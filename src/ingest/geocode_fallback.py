"""
Geocodificador con fallback: intenta múltiples estrategias.

Estrategias:
1. Query completa (lo que ya tenemos)
2. Solo "Spain" en lugar de "Gran Canaria, España"
3. Solo CP + ciudad
4. Solo calle + ciudad (sin CP)

Uso:
    python -m src.ingest.geocode_fallback
"""
import re
import pandas as pd
from pathlib import Path
from typing import Optional, Dict
from geopy.geocoders import Nominatim
import time

from ..config import DATA_RAW_DIR


def clean_address_v2(direccion: str) -> str:
    """Limpia dirección más agresivamente."""
    if not direccion or pd.isna(direccion):
        return None

    direccion = str(direccion).strip()

    if direccion in ("_U", "U", "", "nan"):
        return None

    # Normalizar
    direccion = direccion.replace("Âº", "º").replace("Âª", "ª")
    direccion = re.sub(r"\s+", " ", direccion).strip()

    # Eliminar todo después del número de puerta
    # "Calle Murga 30 Atico B" -> "Calle Murga 30"
    match = re.match(r"^(Calle|Avenida|Plaza|Paseo|Camino|Ronda|Jardines|Pasaje)\s+\S+(?:\s+\S+)?\s*\d+", direccion, re.IGNORECASE)
    if match:
        direccion = match.group(0)

    # Si no tiene número, fallar
    if not re.search(r"\d+", direccion):
        return None

    return direccion


def geocode_with_fallback(direccion: str, cp: str = "") -> Optional[Dict[str, float]]:
    """
    Intenta geocodificar con múltiples estrategias.
    """
    geolocator = Nominatim(user_agent="gc-housing-rag-research")

    # Limpiar dirección
    cleaned = clean_address_v2(direccion)
    if not cleaned:
        return None

    # Normalizar CP
    cp_clean = str(cp) if cp and cp != "_U" else "35001"

    # Estrategias a probar
    queries = [
        # 1. Full query con Spain
        f"{cleaned}, {cp_clean}, Las Palmas de GC, Spain",
        # 2. Sin CP
        f"{cleaned}, Las Palmas de GC, Spain",
        # 3. Con Gran Canaria
        f"{cleaned}, {cp_clean}, Las Palmas de Gran Canaria, Spain",
    ]

    for query in queries:
        try:
            time.sleep(1)  # Rate limit
            location = geolocator.geocode(query, timeout=10)
            if location:
                return {"lat": location.latitude, "lon": location.longitude}
        except Exception:
            continue

    return None


def geocode_fallback():
    """Ejecuta geocodificación con fallback."""
    print("\n🔄 Geocodificación con fallback...")
    print("=" * 60)

    csv_path = DATA_RAW_DIR / "turismo_lpgc_real_geocoded.csv"
    df = pd.read_csv(csv_path)

    # Los que siguen sin coords
    to_geocode = df[(df["lat"] == 0) | (df["lng"] == 0)]
    to_geocode = to_geocode[to_geocode["direccion"] != "_U"]

    print(f"  Total a reintentar: {len(to_geocode)}")

    geocoded = 0

    for idx, row in to_geocode.iterrows():
        direccion = row.get("direccion", "")
        cp = str(row.get("direccion_codigo_postal", ""))

        result = geocode_with_fallback(direccion, cp)

        if result:
            df.at[idx, "lat"] = result["lat"]
            df.at[idx, "lng"] = result["lon"]
            geocoded += 1
            print(f"  ✅ {direccion[:30]}... -> {result['lat']:.4f}, {result['lon']:.4f}")
        else:
            print(f"  ❌ {direccion[:40]}...")

        if geocoded % 20 == 0 and geocoded > 0:
            print(f"\n  📍 Progreso: {geocoded}/{len(to_geocode)}...")

    print("\n" + "=" * 60)
    print(f"  ✅ Geocodificados: {geocoded}")

    # Guardar
    df.to_csv(csv_path, index=False)
    print(f"  💾 Guardado: {csv_path}")

    return df


if __name__ == "__main__":
    geocode_fallback()
