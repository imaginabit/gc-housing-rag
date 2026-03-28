"""
Script para descargar datos reales del ISTAC (Instituto Canario de Estadística).

Datos disponibles:
1. Viviendas vacacionales: ocupación, estancia media, ADR, ingresos (desde 2019)
2. Población por municipio (padrón)

Uso:
    python -m src.ingest.istac_data
"""
import requests
import pandas as pd
from io import StringIO
from pathlib import Path


def download_viviendas_vacacionales() -> pd.DataFrame:
    """
    Descarga datos de viviendas vacacionales del ISTAC.
    Dataset: C00065A_000061 - Estadísticas de turismo de viviendas
    """
    url = 'https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00065A_000061/1.11.csv'
    print('  Descargando viviendas vacacionales...')
    r = requests.get(url, timeout=60)

    # Parse semicolon CSV
    df = pd.read_csv(StringIO(r.text), sep=';', encoding='utf-8')
    df.columns = ['territorio', 'codigo', 'periodo', 'periodo_code',
                  'intervalo_plazas', 'intervalo_plazas_code', 'medida',
                  'medida_code', 'valor', 'notas', 'confidencial', 'estado',
                  'estado_code']

    # Filter: LPGC municipality (codigo starts with 35 and not island level)
    # Las Palmas de GC municipio code: 35010 or similar
    # Let's filter for municipality level (not island _ES70 or island)
    lpgc = df[df['codigo'].astype(str).str.match(r'^35(?!0[01])')].copy()
    print(f'    LPGC + otros: {len(lpgc)} filas')

    # Get unique territory names
    print(f'    Territorios LPGC: {lpgc["territorio"].unique()}')
    return lpgc


def download_poblacion() -> pd.DataFrame:
    """
    Descarga datos de población por municipio del ISTAC.
    Dataset: C00025A_000002 - Población según padrones
    """
    url = 'https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00025A_000002/1.3.csv'
    print('  Descargando población...')
    r = requests.get(url, timeout=60)

    df = pd.read_csv(StringIO(r.text), sep=';', encoding='utf-8')
    print(f'    Columnas: {list(df.columns)}')
    return df


def get_vivienda_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resume datos de vivienda vacacional por periodo y territorio.
    """
    # Solo valores numéricos
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    df = df.dropna(subset=['valor'])

    # Pivot: territorios x medidas x periodo
    pivot = df.pivot_table(
        index=['territorio', 'codigo', 'periodo'],
        columns='medida',
        values='valor',
        aggfunc='first'
    ).reset_index()

    return pivot


def main():
    from src.config import DATA_RAW_DIR

    print("\n📊 Descargando datos reales del ISTAC...")
    print("="*60)

    out = Path(DATA_RAW_DIR)
    out.mkdir(exist_ok=True)

    # 1. Viviendas vacacionales
    print("\n1️⃣ VIVIENDAS VACACIONALES")
    vv = download_viviendas_vacacionales()

    # Save raw
    vv.to_csv(out / 'istac_viviendas_vacacionales.csv', index=False)
    print(f'    ✅ Guardado raw: {len(vv)} filas')

    # Summary
    print(f'\n    Medidas disponibles:')
    for m in vv['medida'].unique():
        print(f'      - {m}')

    print(f'\n    Periodos: {vv["periodo"].min()} a {vv["periodo"].max()}')

    # Save aggregated summary
    summary = get_vivienda_summary(vv)
    summary.to_csv(out / 'istac_viviendas_summary.csv', index=False)
    print(f'    ✅ Guardado summary: {len(summary)} filas')

    # Mostrar LPGC
    lpgc_mun = vv[vv['codigo'].astype(str).str.startswith('3501')]
    print(f'\n    LPGC municipio ({len(lpgc_mun)} filas):')
    if not lpgc_mun.empty:
        medidas_latest = lpgc_mun[lpgc_mun['periodo'] == lpgc_mun['periodo'].max()]
        for _, row in medidas_latest.iterrows():
            print(f'      {row["medida"]}: {row["valor"]}')

    # 2. Población
    print("\n2️⃣ POBLACIÓN")
    pob = download_poblacion()

    # Try to find Las Palmas GC
    pob.columns = ['territorio', 'codigo', 'medida', 'medida_code', 'periodo',
                   'periodo_code', 'valor', 'notas', 'confidencial', 'estado', 'estado_code']

    lpgc_pob = pob[pob['codigo'].astype(str).str.startswith('35')]
    print(f'    LPGC rows: {len(lpgc_pob)}')
    print(f'    sample:')
    print(lpgc_pob[['territorio', 'codigo', 'medida', 'periodo', 'valor']].head(10))


if __name__ == "__main__":
    main()
