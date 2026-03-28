"""
Reverse geocoding: asigna barrio a partir de coordenadas usando point-in-polygon.

Usa los polígonos descargados del ArcGIS del Ayuntamiento de LPGC.

Uso:
    from src.ingest.reverse_geocode import reverse_geocode, load_barrios

    barrio = reverse_geocode(28.099, -15.420)  # Vegueta
"""
import json
from pathlib import Path
from typing import Optional, Dict, List

from shapely.geometry import shape, Point, Polygon, MultiPolygon

# Import config
from ..config import DATA_RAW_DIR

# Archivo de polígonos
BARRIOS_FILE = DATA_RAW_DIR / "barrios_lpgc.json"

# Cache en memoria
_barrios_cache = None
_polygons_cache = None


def load_barrios() -> List[Dict]:
    """Carga los barrios desde el archivo JSON."""
    global _barrios_cache

    if _barrios_cache is None:
        if not BARRIOS_FILE.exists():
            raise FileNotFoundError(
                f"No se encontró {BARRIOS_FILE}. "
                "Ejecuta: python -m src.ingest.download_barrios"
            )

        with open(BARRIOS_FILE, "r", encoding="utf-8") as f:
            geojson = json.load(f)
            _barrios_cache = geojson.get("features", [])

    return _barrios_cache


def get_barrio_polygons() -> Dict[str, shape]:
    """
    Crea un diccionario de polígonos por nombre de barrio.

    Returns:
        Dict {nombre_barrio: shapely.geometry.Polygon}
    """
    global _polygons_cache

    if _polygons_cache is None:
        features = load_barrios()
        _polygons_cache = {}

        for feature in features:
            props = feature.get("properties", {})
            nombre = props.get("NUCL_DS_NOMBRE", "SIN_NOMBRE")

            # Skip diseminados
            if "DISEMINADO" in nombre.upper():
                continue

            geom = feature.get("geometry", {})
            geom_type = geom.get("type")

            if geom_type == "Polygon":
                # GeoJSON: [[lon, lat], [lon, lat], ...]
                # Polygon acepta directamente este formato
                rings = geom.get("coordinates", [])
                if rings and rings[0]:
                    polygon = Polygon(rings[0])
                    _polygons_cache[nombre] = polygon

            elif geom_type == "MultiPolygon":
                # MultiPolygon: [[[lon, lat], ...], [[lon, lat], ...], ...]
                polys = geom.get("coordinates", [])
                if polys:
                    mpoly = MultiPolygon([(poly, []) for poly in polys])
                    _polygons_cache[nombre] = mpoly

    return _polygons_cache


def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """
    Asigna barrio a partir de coordenadas usando point-in-polygon.

    Args:
        lat: Latitud
        lon: Longitud

    Returns:
        Nombre del barrio o None si no está dentro de ningún polígono.
    """
    # Validar coordenadas
    if lat == 0.0 and lon == 0.0:
        return None

    # Gran Canaria: lat 27.0-28.2, lon -15.0 to -16.0
    if not (27.0 < lat < 28.2) or not (-16.0 < lon < -15.0):
        # Coordenadas fuera de Gran Canaria
        return None

    # Crear punto (shapely usa x=lon, y=lat)
    point = Point(lon, lat)

    # Buscar en polígonos
    polygons = get_barrio_polygons()

    for nombre, polygon in polygons.items():
        if polygon.contains(point):
            return nombre

    return None


def reverse_geocode_batch(coords_list: List[tuple]) -> List[Optional[str]]:
    """
    Reverse geocoding para una lista de coordenadas.

    Args:
        coords_list: Lista de tuplas (lat, lon)

    Returns:
        Lista de nombres de barrio
    """
    return [reverse_geocode(lat, lon) for lat, lon in coords_list]


def get_barrios_stats() -> Dict[str, int]:
    """Retorna estadísticas de barrios cargados."""
    polygons = get_barrio_polygons()
    return {
        "total_barrios": len(polygons),
        "barrios": sorted(polygons.keys()),
    }


if __name__ == "__main__":
    print("\n🧪 Test reverse geocode:")

    # Test puntos conocidos
    test_points = [
        (28.099, -15.420, "Vegueta"),  # Centro histórico
        (28.124, -15.436, "Canteras"),  # Playa
        (28.112, -15.456, "Triana"),    # Triana
    ]

    polygons = get_barrio_polygons()
    print(f"  📊 Barrios cargados: {len(polygons)}")

    for lat, lon, expected in test_points:
        result = reverse_geocode(lat, lon)
        status = "✅" if result else "❌"
        print(f"  {status} ({lat}, {lon}) → {result} (esperado: {expected})")
