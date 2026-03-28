"""
Geocodificador de direcciones usando Nominatim (OpenStreetMap).

Funciones:
- geocode_address(): Convierte dirección a lat/lon
- Cache en archivo JSON para evitar requests duplicados
- Rate limiting: 1 request por segundo

Uso:
    from src.ingest.geocoder import geocode_address

    result = geocode_address("Calle Mayor 15, Las Palmas de GC", "35003")
    # result = {"lat": 28.099, "lon": -15.420}
"""
import json
import time
import os
from pathlib import Path
from typing import Optional, Dict
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Import config
from ..config import DATA_RAW_DIR

# Inicializar Nominatim
geolocator = Nominatim(user_agent="gc-housing-rag-research")

# Archivo de cache
CACHE_FILE = DATA_RAW_DIR / "geocode_cache.json"

# Rate limiting
LAST_REQUEST_TIME = 0.0
MIN_REQUEST_INTERVAL = 1.0  # 1 segundo entre requests


def _load_cache() -> Dict[str, dict]:
    """Carga el cache desde archivo JSON."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: Dict[str, dict]):
    """Guarda el cache en archivo JSON."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _rate_limit():
    """Espera si es necesario para respetar el rate limit."""
    global LAST_REQUEST_TIME
    now = time.time()
    elapsed = now - LAST_REQUEST_TIME

    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)

    LAST_REQUEST_TIME = time.time()


def geocode_address(direccion: str, cp: str = "") -> Optional[Dict[str, float]]:
    """
    Geocodifica una dirección usando Nominatim.

    Args:
        direccion: Dirección de la vivienda (ej: "Calle Murga 30")
        cp: Código postal (ej: "35003")

    Returns:
        Dict con 'lat' y 'lon', o None si no se encuentra.
    """
    if not direccion:
        return None

    # Construir query
    parts = [direccion]
    if cp:
        parts.append(cp)
    parts.extend(["Las Palmas de Gran Canaria", "Gran Canaria", "España"])
    query = ", ".join(parts)

    # Verificar cache
    cache = _load_cache()
    cache_key = query.lower().strip()

    if cache_key in cache:
        cached = cache[cache_key]
        if cached.get("lat") and cached.get("lon"):
            print(f"  📍 Cache hit: {direccion[:30]}...")
            return {"lat": cached["lat"], "lon": cached["lon"]}

    # Rate limiting antes de request
    _rate_limit()

    # Realizar geocodificación
    try:
        print(f"  🌐 Geocodificando: {direccion[:40]}...")
        location = geolocator.geocode(query, timeout=10)

        if location:
            result = {"lat": location.latitude, "lon": location.longitude}
            # Guardar en cache
            cache[cache_key] = result
            _save_cache(cache)
            print(f"    ✅ {location.latitude:.5f}, {location.longitude:.5f}")
            return result
        else:
            # Guardar fallo en cache para no reintentar
            cache[cache_key] = {"lat": None, "lon": None, "error": "not_found"}
            _save_cache(cache)
            print(f"    ❌ No encontrado")
            return None

    except GeocoderTimedOut:
        print(f"    ⏱️ Timeout, reintentando...")
        # Reintentar una vez
        time.sleep(2)
        try:
            location = geolocator.geocode(query, timeout=10)
            if location:
                result = {"lat": location.latitude, "lon": location.longitude}
                cache[cache_key] = result
                _save_cache(cache)
                return result
        except Exception:
            pass
        return None

    except GeocoderServiceError as e:
        print(f"    ⚠️ Error de servicio: {e}")
        return None

    except Exception as e:
        print(f"    ❌ Error: {e}")
        return None


def geocode_batch(direcciones: list, start_index: int = 0) -> list:
    """
    Geocodifica una lista de direcciones.

    Args:
        direcciones: Lista de tuplas (direccion, cp)
        start_index: Índice inicial para mostrar progreso

    Returns:
        Lista de dicts con lat, lon
    """
    results = []
    total = len(direcciones)

    for i, (direccion, cp) in enumerate(direcciones, start=1):
        print(f"  [{i}/{total}] ", end="")
        result = geocode_address(direccion, cp)
        results.append(result)

    return results


if __name__ == "__main__":
    # Test rápido
    print("\n🧪 Test geocoder:")
    test_cases = [
        ("Calle Murga 30", "35003"),
        ("Calle Mayor 15", "35003"),
        ("Playa de las Canteras", "35010"),
    ]

    for direccion, cp in test_cases:
        result = geocode_address(direccion, cp)
        print(f"  {direccion}: {result}")
