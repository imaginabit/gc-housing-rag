"""
Geocodifica las viviendas que tienen coordenadas 0,0.

Uso:
    python -m src.ingest.geocode_missing
"""
import pandas as pd
from pathlib import Path

from ..config import DATA_RAW_DIR
from .geocoder import geocode_address


def geocode_missing():
    """Geocodifica las vv con coords=0 y guarda resultados."""
    print("\n🔄 Geocodificando viviendas sin coords...")
    print("=" * 60)

    # Cargar datos
    csv_path = DATA_RAW_DIR / "turismo_lpgc_real.csv"
    df = pd.read_csv(csv_path)

    # Filtrar los que tienen coords=0
    to_geocode = df[(df["lat"] == 0) | (df["lng"] == 0)]

    print(f"  Total a geocodificar: {len(to_geocode)}")
    print(f"  (Esto tomará ~{len(to_geocode)} segundos)")

    # Geocodificar cada uno
    geocoded = 0
    failed = 0

    for idx, row in to_geocode.iterrows():
        direccion = row.get("direccion", "")
        cp = str(row.get("direccion_codigo_postal", ""))

        print(f"  [{geocoded + failed}] ", end="")

        result = geocode_address(direccion, cp)

        if result:
            df.at[idx, "lat"] = result["lat"]
            df.at[idx, "lng"] = result["lon"]
            geocoded += 1
        else:
            failed += 1

        if (geocoded + failed) % 100 == 0:
            print(f"\n  📍 Progreso: {geocoded + failed}/{len(to_geocode)}...")

    print("\n" + "=" * 60)
    print(f"  ✅ Geocodificados: {geocoded}")
    print(f"  ❌ Fallidos: {failed}")

    # Guardar
    output_path = DATA_RAW_DIR / "turismo_lpgc_real_geocoded.csv"
    df.to_csv(output_path, index=False)
    print(f"\n  💾 Guardado: {output_path}")

    return df


if __name__ == "__main__":
    geocode_missing()
