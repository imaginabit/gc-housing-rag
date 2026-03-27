"""
Ingesta de datos de población del INE.

El INE proporciona datos de padrón por secciones censales.
Municipio Las Palmas de GC = 35020

Los datos se descargan desde:
https://www.ine.es/celDisconnected_files/ celdaspadr.htm

Notas:
- El INE usa códigos de provincia/municipio/sección
- LPGC (35020) tiene ~33 secciones censales (barrios)
- Disponibles desde 1996 hasta latest año
"""
import pandas as pd
import requests
import io
import re
from pathlib import Path
from ..config import DATA_RAW_DIR, INE_MUNICIPIO


# Códigos de las secciones censales de LPGC (aproximados)
# En producción se obtendrían dinámicamente desde la primera descarga
SECCIONES_LPGC = {
    "35020": "Las Palmas de Gran Canaria (total)",
}

# Años disponibles
ANOS = list(range(2015, 2025))


def build_ine_url(ano: int, municipio: str = "35020") -> str:
    """
    Construye la URL de descarga del INE para un año y municipio dados.
    
    El INE tiene una URL pattern para downloads CSV:
    https://www.ine.es/censo2021/ficheros/35/35{municipio}_{ano}.csv
    """
    # URL directa para datos de padrón - formato CSV
    # El INE ofrece descarga directa de ficheros de población
    
    # Census 2021 - padrón por secciones
    url = f"https://ine.es/ficheros/censo2021/fpdatos/35/35{municipio}_{ano}.csv"
    return url


def download_ine_csv(ano: int, municipio: str = "35020") -> pd.DataFrame:
    """
    Descarga datos de población del INE para un año concreto.
    
    Returns:
        DataFrame con columnas: seccion, ano, poblacion
    """
    url = build_ine_url(ano, municipio)
    
    print(f"  Descargando {ano} desde {url}...")
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        
        # El INE devuelve CSV con encoding iso-8859-1
        df = pd.read_csv(
            io.StringIO(resp.text),
            encoding='iso-8859-1',
            sep=';',
            header=None,
            names=['seccion', 'poblacion']
        )
        
        # Limpiar datos
        df['ano'] = ano
        df['municipio'] = municipio
        df['seccion'] = df['seccion'].astype(str).str.strip()
        df['poblacion'] = pd.to_numeric(df['poblacion'].astype(str).str.replace('.', '').str.strip(), errors='coerce')
        
        # Filtrar solo LPGC (código 35020)
        df = df[df['seccion'].str.startswith('35020')]
        
        return df[['seccion', 'ano', 'poblacion', 'municipio']]
        
    except requests.exceptions.RequestException as e:
        print(f"  ⚠ Error descargando {ano}: {e}")
        return pd.DataFrame()


def fetch_ine_population(anos: list = ANOS, municipio: str = INE_MUNICIPIO) -> pd.DataFrame:
    """
    Descarga datos de población del INE para todos los años.
    
    Args:
        anos: lista de años a descargar
        municipio: código INE del municipio (default: 35020 = LPGC)
    
    Returns:
        DataFrame consolidado con poblacion por seccion y año
    """
    print(f"\n📊 Descargando datos de población INE ({municipio})...")
    
    all_data = []
    for ano in anos:
        df = download_ine_csv(ano, municipio)
        if not df.empty:
            all_data.append(df)
        else:
            # Intentar con URL alternativa
            df = download_ine_alternative(ano, municipio)
            if not df.empty:
                all_data.append(df)
    
    if not all_data:
        print("  ⚠ No se pudieron descargar datos del INE")
        return pd.DataFrame()
    
    result = pd.concat(all_data, ignore_index=True)
    
    # Guardar raw
    raw_path = DATA_RAW_DIR / "ine_population_raw.csv"
    result.to_csv(raw_path, index=False)
    print(f"  ✅ Guardado en {raw_path} ({len(result)} registros)")
    
    return result


def download_ine_alternative(ano: int, municipio: str = "35020") -> pd.DataFrame:
    """
    URL alternativa para descarga INE.
    """
    # Intentar con el formato del padrón anual
    url = f"https://ine.es/pob/pobmunic.zip"
    
    print(f"  Intentando descarga alternativa para {ano}...")
    
    # Esta función se implementaría si la principal falla
    # Por ahora devolvemos dataframe vacío
    return pd.DataFrame()


def get_barrio_mapping() -> dict:
    """
    Devuelve el mapeo de códigos de sección -> nombre de barrio.
    
    Las secciones censales del INE son códigos numéricos.
    Necesitamos un mapeo manual para los barrios de LPGC.
    
    Returns:
        Dict con {codigo_seccion: nombre_barrio}
    """
    # Mapeo aproximado de secciones -> barrios de LPGC
    # Se obtiene de analizar los datos descargados o de fuentes externas
    return {
        "3502001": "Vegueta",
        "3502002": "Vegueta",
        "3502003": "Triana",
        "3502004": "Triana",
        "3502005": "Mesa y López",
        "3502006": "Mesa y López",
        "3502007": "Playa de las Canteras",
        "3502008": "Playa de las Canteras",
        "3502009": "La Isleta",
        "3502010": "La Isleta",
        # ... más secciones
    }


def process_ine_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Procesa los datos crudos del INE y los enriquece con nombres de barrio.
    
    Args:
        df: DataFrame de población cruda
    
    Returns:
        DataFrame procesado con columna 'barrio' añadida
    """
    if df.empty:
        return df
    
    # Obtener mapeo de barrios
    barrio_map = get_barrio_mapping()
    
    # Añadir columna de barrio (por prefijo de sección)
    def get_barrio(seccion):
        seccion = str(seccion)
        for code, name in barrio_map.items():
            if seccion.startswith(code[:5]):
                return name
        return "Otro"
    
    df['barrio'] = df['seccion'].apply(get_barrio)
    
    # Guardar procesado
    processed_path = DATA_RAW_DIR / "ine_population_processed.csv"
    df.to_csv(processed_path, index=False)
    
    return df
