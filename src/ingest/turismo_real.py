"""
[DEPRECATED] Variante experimental de turismo.py — usar turismo.py en su lugar.

Script para descargar datos reales de viviendas turísticas de Canarias.

El Gobierno de Canarias tiene un registro abierto de viviendas turísticas.
URL: https://www.turismo.grancanaria.com/es/registro-turistico

Uso:
    python -m src.ingest.turismo_real
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# El registro de turismo de Canarias tiene datos en formato CSV/Excel
# Disponibles en el portal de datos abiertos del Gobierno de Canarias

REGISTRO_URL = "https://datos.canarias.es/catalogos/turismo-viviendas"


def get_turismo_data() -> pd.DataFrame:
    """
    Intenta descargar datos del registro de turismo de Canarias.

    Returns:
        DataFrame con columnas: barrio, direccion, tipo, plazas, registro, ano_registro
    """
    print("  Intentando descargar del portal de datos abiertos de Canarias...")

    # URLs conocidas del registro de turismo
    urls_to_try = [
        # Intentar directamente desde el Gobierno de Canarias
        "https://www.turismo.grancanaria.com/doc/registro-viviendas-turisticas.csv",
        # Datos abiertos de Canarias
        "https://datos.canarias.es/api/estadisticas/turismo-viviendas",
        # Intentar con formato específico
        "https://datos.canarias.es/data/turismo/viviendas-turisticas-lpgc.csv",
    ]

    for url in urls_to_try:
        print(f"  Probando: {url[:60]}...")
        try:
            resp = requests.get(url, timeout=30, allow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 1000:
                print(f"    ✅ Datos encontrados ({len(resp.content)} bytes)")

                # Intentar parsear como CSV
                try:
                    df = pd.read_csv(url, encoding="utf-8")
                    return df
                except:
                    pass
                try:
                    df = pd.read_csv(url, encoding="latin-1")
                    return df
                except:
                    pass
                try:
                    df = pd.read_excel(url)
                    return df
                except:
                    pass
        except Exception as e:
            print(f"    Error: {e}")

    print("  No se pudo acceder a datos en línea")
    return pd.DataFrame()


def get_sample_from_gobierno_canarias() -> pd.DataFrame:
    """
    Intenta hacer scraping básico del registro de turismo.

    Returns:
        DataFrame con datos si se pudieron obtener
    """
    print("  Intentando scraping básico del registro...")

    try:
        # Acceso a la página principal del registro
        url = "https://www.turismo.grancanaria.com/es/registro-turistico"
        resp = requests.get(url, timeout=30)

        if resp.status_code == 200:
            print(f"    ✅ Página del registro accesible")
            # Aquí se implementaría el scraping real
            # Por ahora devolvemos dataframe vacío
    except Exception as e:
        print(f"    Error: {e}")

    return pd.DataFrame()


def main():
    from src.config import DATA_RAW_DIR

    print("\n🏠 Descargando datos reales de viviendas turísticas...")
    print(f"   Registro: Turismo de Canarias\n")

    df = get_turismo_data()

    if df.empty:
        print("\n⚠️ No se pudieron descargar datos automáticos.")
        print("   Opciones para obtener datos reales:")
        print("   1. Solicitar formalmente al Gobierno de Canarias")
        print("   2. Hacer scraping manual del registro")
        print("   3. Usar datos de Inside Airbnb (alternativa)")
        return

    print(f"\n✅ Datos obtenidos: {len(df)} registros")
    print(df.head())


if __name__ == "__main__":
    main()
