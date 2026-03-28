"""
Pipeline para asignar barrios a viviendas vacacionales.

PROCESO OPTIMIZADO:
1. Cargar turismo_lpgc_real.csv
2. Para cada fila con coords válidas + barrio="_U", asignar barrio
3. Guardar CSV actualizado

NO necesita geocodificación - los datos ya tienen coords.

Uso:
    python -m src.ingest.assign_barrios
"""
import pandas as pd
from pathlib import Path

from ..config import DATA_RAW_DIR
from .reverse_geocode import reverse_geocode


def is_valid_coords(lat, lng) -> bool:
    """Verifica si las coordenadas son válidas para Gran Canaria."""
    if pd.isna(lat) or pd.isna(lng):
        return False
    if lat == 0.0 or lng == 0.0:
        return False
    if not (27.0 < lat < 28.2 and -16.0 < lng < -15.0):
        return False
    return True


def assign_barrios_to_turismo(limit: int = None) -> pd.DataFrame:
    """
    Asigna barrio a cada vivienda según sus coordenadas.

    Args:
        limit: Límite de registros para testing

    Returns:
        DataFrame con columna 'barrio_asignado'
    """
    print("\n🏘️ Asignando barrios a viviendas vacacionales...")
    print("=" * 60)

    # Cargar datos
    csv_path = DATA_RAW_DIR / "turismo_lpgc_real_geocoded.csv"
    df = pd.read_csv(csv_path)

    if limit:
        df = df.head(limit)

    total = len(df)
    print(f"  Total viviendas: {total}")

    # Contadores
    with_valid_coords = 0
    already_has_barrio = 0
    assigned = 0
    failed = 0

    # Añadir columna si no existe
    if "barrio_asignado" not in df.columns:
        df["barrio_asignado"] = None

    # Procesar cada fila
    for idx, row in df.iterrows():
        if limit and idx >= limit:
            break

        if idx % 500 == 0:
            print(f"  📍 Procesando {idx}/{total}...")

        lat = row.get("lat")
        lng = row.get("lng")
        current_barrio = row.get("barrio", "_U")

        # Skip si ya tiene barrio válido
        if current_barrio and current_barrio != "_U":
            already_has_barrio += 1
            df.at[idx, "barrio_asignado"] = current_barrio
            continue

        # Verificar coords válidas
        if not is_valid_coords(lat, lng):
            failed += 1
            continue

        with_valid_coords += 1

        # Reverse geocoding
        barrio = reverse_geocode(lat, lng)
        if barrio:
            df.at[idx, "barrio_asignado"] = barrio
            assigned += 1
        else:
            # Mantener el original
            df.at[idx, "barrio_asignado"] = current_barrio

    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN:")
    print(f"  📍 Con coords válidas: {with_valid_coords}")
    print(f"  🏷️ Ya tenía barrio: {already_has_barrio}")
    print(f"  ✅ Barrio asignado: {assigned}")
    print(f"  ❌ Sin coords: {failed}")

    # Coverage
    with_barrio = df["barrio_asignado"].notna().sum()
    coverage = (with_barrio / len(df)) * 100
    print(f"\n  📈 Coverage: {coverage:.1f}% ({with_barrio}/{len(df)})")

    return df


def save_results(df: pd.DataFrame):
    """Guarda el CSV actualizado."""
    output_path = DATA_RAW_DIR / "turismo_lpgc_with_barrios.csv"
    df.to_csv(output_path, index=False)
    print(f"\n  💾 Guardado: {output_path}")
    return output_path


def main():
    """Ejecuta el pipeline."""
    df = assign_barrios_to_turismo(limit=None)
    save_results(df)

    # Stats por barrio
    print("\n📊 Distribución por barrio:")
    print(df["barrio_asignado"].value_counts().head(20))

    print("\n" + "=" * 60)
    print("✅ 完成")


if __name__ == "__main__":
    main()
