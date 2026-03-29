"""
[DEPRECATED] Variante experimental de ine.py — usar ine.py en su lugar.

Script para descargar datos reales de INE (población por secciones censales).

Uso:
    python -m src.ingest.ine_real
"""

import requests
import pandas as pd
import io
import re
from pathlib import Path

# URL del INE - padrón por municipios
# El INE tiene los datos en formato CSV accessible via their web
INE_BASE = "https://www.ine.es"

# Municipio Las Palmas de GC = 35020
MUNICIPIO = "35020"


def get_ine_population_by_year(municipio: str = MUNICIPIO) -> pd.DataFrame:
    """
    Descarga datos de población del INE para un municipio.

    El INE tiene una API para datos de padrón:
    https://servicios.ine.es/ws/datospoblacion/v1

    Returns:
        DataFrame con columnas: seccion, ano, poblacion
    """
    all_data = []

    for ano in range(2015, 2025):
        url = (
            f"https://www.ine.es/ficheros/censo2021/fpdatos/35/35{municipio}_{ano}.csv"
        )
        print(f"  Descargando {ano}...")

        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                # El INE usa encoding iso-8859-1
                df = pd.read_csv(
                    io.StringIO(resp.text),
                    encoding="iso-8859-1",
                    sep=";",
                    header=None,
                    names=["seccion", "poblacion"],
                    dtype={"seccion": str},
                )

                # Limpiar seccion y poblacion
                df["seccion"] = df["seccion"].str.strip()
                df["poblacion"] = pd.to_numeric(
                    df["poblacion"].astype(str).str.replace(".", "").str.strip(),
                    errors="coerce",
                )
                df["ano"] = ano
                df["municipio"] = municipio

                # Filtrar solo secciones de LPGC (empiezan con 35020)
                df = df[df["seccion"].str.startswith("35020")]

                all_data.append(df)
                print(f"    OK: {len(df)} secciones")
            else:
                print(f"    Error: HTTP {resp.status_code}")
        except Exception as e:
            print(f"    Error: {e}")

    if not all_data:
        return pd.DataFrame()

    result = pd.concat(all_data, ignore_index=True)
    return result[["seccion", "ano", "poblacion", "municipio"]]


def get_section_to_barrio_mapping() -> dict:
    """
    Mapping de códigos de sección censal a nombre de barrio.

    Las secciones censales del INE para LPGC:
    - 3502001* a 3502003* -> Vegueta
    - 3502004* a 3502006* -> Triana
    - 3502007* a 3502009* -> Mesa y López
    - 3502010* a 3502012* -> Playa de las Canteras
    - 3502013* a 3502014* -> La Isleta
    - etc.
    """
    mapping = {}

    # Vegueta: secciones 001, 002, 003
    for i in range(1, 4):
        for j in range(1, 10):
            mapping[f"35020{i:02d}{j:02d}"] = "Vegueta"

    # Triana: secciones 004, 005, 006
    for i in range(4, 7):
        for j in range(1, 10):
            mapping[f"35020{i:02d}{j:02d}"] = "Triana"

    # Mesa y López: secciones 007, 008, 009
    for i in range(7, 10):
        for j in range(1, 10):
            mapping[f"35020{i:02d}{j:02d}"] = "Mesa y López"

    # Playa de las Canteras: secciones 010, 011, 012
    for i in range(10, 13):
        for j in range(1, 10):
            mapping[f"35020{i:02d}{j:02d}"] = "Playa de las Canteras"

    # La Isleta: secciones 013, 014
    for i in range(13, 15):
        for j in range(1, 10):
            mapping[f"35020{i:02d}{j:02d}"] = "La Isleta"

    return mapping


def assign_barrio(df: pd.DataFrame) -> pd.DataFrame:
    """Asigna barrio a cada registro basándose en la sección censal."""
    mapping = get_section_to_barrio_mapping()

    def find_barrio(seccion):
        seccion = str(seccion).strip()
        # Intentar coincidencia exacta primero
        if seccion in mapping:
            return mapping[seccion]
        # Buscar por prefijo
        for i in range(len(seccion), 3, -1):
            prefix = seccion[:i]
            if prefix in mapping:
                return mapping[prefix]
        return "Otro"

    df["barrio"] = df["seccion"].apply(find_barrio)
    return df


def main():
    from src.config import DATA_RAW_DIR, INE_MUNICIPIO

    print(f"\n📊 Descargando datos reales del INE...")
    print(f"   Municipio: {INE_MUNICIPIO} (Las Palmas de GC)")
    print(f"   Años: 2015-2024\n")

    # Descargar datos
    df = get_ine_population_by_year(INE_MUNICIPIO)

    if df.empty:
        print("No se pudieron descargar datos del INE")
        return

    # Asignar barrios
    df = assign_barrio(df)

    # Guardar
    output_path = DATA_RAW_DIR / "ine_population_real.csv"
    df.to_csv(output_path, index=False)

    print(f"\n✅ Guardado: {output_path}")
    print(f"   Total registros: {len(df)}")
    print(f"   Años: {df['ano'].min()} - {df['ano'].max()}")
    print(f"\n   Por barrio:")
    summary = df.groupby("barrio").agg(
        secciones=("seccion", "nunique"),
        pob_2015=("poblacion", lambda x: x[df["ano"] == 2015].sum()),
        pob_2024=("poblacion", lambda x: x[df["ano"] == 2024].sum()),
    )
    print(summary)


if __name__ == "__main__":
    main()
