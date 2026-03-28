"""
Descarga polígonos de barrios desde el ArcGIS REST API del Ayuntamiento de LPGC.

URL: https://sit.laspalmasgc.es/server/rest/services/opendata/barrios/MapServer/0/query?where=1%3D1&outFields=*&f=geojson

Uso:
    python -m src.ingest.download_barrios
"""
import json
import requests
from pathlib import Path

# URL oficial del Ayuntamiento de Las Palmas de GC
BARRIOS_GEOJSON_URL = (
    "https://sit.laspalmasgc.es/server/rest/services/opendata/barrios/MapServer/0/query"
    "?where=1%3D1"
    "&outFields=*"
    "&f=geojson"
)


def download_barrios_arcgis() -> dict:
    """
    Descarga polígonos de barrios desde ArcGIS REST API.

    Returns:
        GeoJSON dict con features por barrio.
        Cada feature tiene propiedades['NUCL_DS_NOMBRE'] con el nombre del barrio.
    """
    print(f"  Descargando polígonos de barrios desde ArcGIS...")
    print(f"  URL: {BARRIOS_GEOJSON_URL[:80]}...")

    response = requests.get(BARRIOS_GEOJSON_URL, timeout=60)
    response.raise_for_status()

    geojson = response.json()

    # Verificar estructura
    if "features" not in geojson:
        raise ValueError(f"GeoJSON inválido: no tiene 'features'")

    print(f"  ✅ Descargados {len(geojson['features'])} barrios")

    return geojson


def save_barrios(geojson: dict, output_path: Path):
    """Guarda el GeoJSON en archivo."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"  ✅ Guardado en: {output_path}")


def main():
    from src.config import DATA_RAW_DIR

    print("\n📥 Descargando barrios de LPGC...")
    print("=" * 60)

    # Descargar
    geojson = download_barrios_arcgis()

    # Mostrar nombres de barrios
    print("\n  Barrios encontrados:")
    for feature in geojson["features"]:
        nombre = feature.get("properties", {}).get("NUCL_DS_NOMBRE", "SIN_NOMBRE")
        print(f"    - {nombre}")

    # Guardar
    output_path = DATA_RAW_DIR / "barrios_lpgc.json"
    save_barrios(geojson, output_path)

    print("\n" + "=" * 60)
    print(f"✅完成: {len(geojson['features'])} barrios descargados")


if __name__ == "__main__":
    main()
