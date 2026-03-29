"""
[ONE-TIME] Pipeline step — ya ejecutado. Los datos limpios están en data/raw/.

Limpia direcciones problemáticas y reintenta geocodificación.

Problema: Muchas direcciones tienen formato incompatible con Nominatim:
- "Calle Murga 30 Atico B" → "Calle Murga 30"
- "Calle Rosarito 10 2 Izquierda" → "Calle Rosarito 10"

Uso:
    python -m src.ingest.geocode_clean
"""

import re
import pandas as pd
from pathlib import Path

from ..config import DATA_RAW_DIR
from .geocoder import geocode_address


def clean_address(direccion: str) -> str:
    """
    Limpia dirección extrayendo solo calle + número.

    Returns:
        Dirección limpia o None si es irreconocible (_U, vacío)
    """
    if not direccion or pd.isna(direccion):
        return None

    direccion = str(direccion).strip()

    # Ignorar valores inválidos
    if direccion in ("_U", "U", "", "nan"):
        return None

    # Eliminar acentos extraños y normalizar
    direccion = direccion.replace("Âº", "º").replace("Âª", "ª")

    # Patrones a eliminar (piso, puerta, escalera, etc.)
    # Orden importante: primero los más específicos
    eliminables = [
        r"\s+Escalera\s+\w+",  # Escalera A, Escalera 3
        r"\s+Planta\s+\w+",  # Planta 1, Planta Baja
        r"\s+Piso\s+\d+",  # Piso 1, Piso 2
        r"\s+\d+\s*[ªº]\s*[A-Z]?\s*$",  # 1º, 2ºA, 3ºB al final
        r"\s+\d+\s*[ªº]\s*[A-Z]?",  # 1ºA, 2ºB en medio
        r"\s+Atico\s*[A-Z]?",  # Atico, Atico A
        r"\s+Entreplanta\s*\d*",  # Entreplanta, Entreplanta 1
        r"\s+Izquierda\s*$",  # ...Izquierda
        r"\s+Derecha\s*$",  # ...Derecha
        r"\s+Interior\s*\d*",  # Interior, Interior 1
        r"\s+Oficina\s*\d*",  # Oficina, Oficina 1
        r"\s+Local\s*\d*",  # Local, Local 1
        r"\s+Nave\s*\d*",  # Nave, Nave 1
        r"\s+Bloque\s*\w+",  # Bloque A, Bloque 1
        r"\s+Portal\s*\w+",  # Portal 1, Portal A
        r"\s+\d+\s*\d+\s*\d+\s*$",  # 重复数字: 94 94 2 202
    ]

    for patron in eliminables:
        direccion = re.sub(patron, "", direccion, flags=re.IGNORECASE)

    # Limpiar espacios múltiples
    direccion = re.sub(r"\s+", " ", direccion).strip()

    # Verificar que queda algo válido (al menos calle + número)
    if not re.search(r"\d+", direccion):
        return None  # Sin número no tiene sentido

    if len(direccion) < 5:
        return None

    return direccion


def geocode_clean():
    """Limpia direcciones y reintenta geocodificación."""
    print("\n🔄 Limpiando direcciones y reintentando geocodificación...")
    print("=" * 60)

    # Cargar datos geocodificados previamente
    csv_path = DATA_RAW_DIR / "turismo_lpgc_real_geocoded.csv"
    df = pd.read_csv(csv_path)

    # Filtrar los que siguen con coords=0
    to_geocode = df[(df["lat"] == 0) | (df["lng"] == 0)]

    print(f"  Total sin coords: {len(to_geocode)}")

    # Contadores
    geocoded = 0
    failed = 0
    skipped = 0

    for idx, row in to_geocode.iterrows():
        original = row.get("direccion", "")
        cp = str(row.get("direccion_codigo_postal", ""))

        # Limpiar dirección
        cleaned = clean_address(original)

        if not cleaned:
            skipped += 1
            print(f"  [{geocoded + failed + skipped}] ⏭️  Saltado: {original[:30]}...")
            continue

        # Si la dirección ya era igual, no bother
        if cleaned == original.strip():
            skipped += 1
            continue

        print(f"  [{geocoded + failed + skipped}] 🔧 ", end="")
        print(f"'{original[:25]}...' → '{cleaned[:25]}...'")

        result = geocode_address(cleaned, cp if cp != "_U" else "35001")

        if result:
            df.at[idx, "lat"] = result["lat"]
            df.at[idx, "lng"] = result["lon"]
            geocoded += 1
        else:
            failed += 1

        # Mostrar progreso cada 50
        if (geocoded + failed) % 50 == 0:
            print(f"\n  📍 Progreso: {geocoded + failed}/{len(to_geocode)}...")

    print("\n" + "=" * 60)
    print(f"  ✅ Geocodificados: {geocoded}")
    print(f"  ❌ Fallidos: {failed}")
    print(f"  ⏭️  Saltados: {skipped}")

    # Guardar
    output_path = DATA_RAW_DIR / "turismo_lpgc_real_geocoded.csv"
    df.to_csv(output_path, index=False)
    print(f"\n  💾 Guardado: {output_path}")

    return df


if __name__ == "__main__":
    geocode_clean()
