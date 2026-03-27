"""
Ingesta de datos de viviendas turísticas de Gran Canaria.

El Gobierno de Canarias tiene un registro público de viviendas turísticas:
https://www.turismo.grancanaria.com/es/registro-turistico

Cada vivienda tiene:
- Número de registro
- Dirección
- Municipio
- Tipo (vivienda vacacional, apartamento turístico, etc.)
- Plazas

Datos públicos disponibles en formato que varía según la época.
"""
import pandas as pd
import requests
import io
from pathlib import Path
from ..config import DATA_RAW_DIR


# URL del registro de turismo de Canarias (formato abierto)
REGISTRO_URL = "https://datos.canarias.es/data/"

# Datos manualmente compilados de ejemplo para desarrollo
# En producción se scrappería o pediría formalmente
SAMPLE_DATA = {
    "viviendas_turisticas_lpgc": [
        {"barrio": "Vegueta", "direccion": "Calle Doctorado 5", "tipo": "Vivienda Vacacional", "plazas": 4, "registro": "VT-35-XXXX"},
        {"barrio": "Triana", "direccion": "Calle Mayor de Triana 42", "tipo": "Vivienda Vacacional", "plazas": 6, "registro": "VT-35-YYYY"},
        {"barrio": "Playa de las Canteras", "direccion": "Avda. beach 12", "tipo": "Apartamento Turístico", "plazas": 4, "registro": "AT-35-ZZZZ"},
    ]
}


def fetch_turismo_data() -> pd.DataFrame:
    """
    Obtiene datos de viviendas turísticas de LPGC.
    
    En producción esto scrappería el registro oficial.
    Por ahora usa datos de ejemplo para desarrollar.
    
    Returns:
        DataFrame con columnas: barrio, direccion, tipo, plazas, registro
    """
    print("\n🏠 Descargando datos de viviendas turísticas...")
    
    # Intentar descargar del registro abierto de Canarias
    try:
        # El Gobierno de Canarias tiene datos abiertos en:
        # https://datos.canarias.es/catalogos/ abertos/
        url = f"{REGISTRO_URL}turismo-viviendas"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        
        # Parsear según formato (CSV, JSON, XLS...)
        df = parse_turismo_format(resp)
        
    except Exception as e:
        print(f"  ⚠ No se pudo acceder al registro: {e}")
        print("  → Usando datos de ejemplo para desarrollo")
        df = get_sample_data()
    
    # Guardar raw
    raw_path = DATA_RAW_DIR / "turismo_viviendas.csv"
    df.to_csv(raw_path, index=False)
    print(f"  ✅ Guardado en {raw_path} ({len(df)} registros)")
    
    return df


def parse_turismo_format(resp: requests.Response) -> pd.DataFrame:
    """
    Parsea la respuesta del registro de turismo según content-type.
    """
    content_type = resp.headers.get('Content-Type', '')
    
    if 'csv' in content_type:
        return pd.read_csv(io.StringIO(resp.text))
    elif 'json' in content_type:
        return pd.read_json(io.StringIO(resp.text))
    elif 'excel' in content_type or 'spreadsheet' in content_type:
        return pd.read_excel(io.BytesIO(resp.content))
    else:
        # Intentar detectar formato
        text = resp.text
        if text.strip().startswith('{') or text.strip().startswith('['):
            return pd.read_json(io.StringIO(text))
        elif ',' in text.split('\n')[0]:
            return pd.read_csv(io.StringIO(text))
        else:
            raise ValueError(f"Formato no reconocido: {content_type}")


def get_sample_data() -> pd.DataFrame:
    """
    Devuelve datos de ejemplo para desarrollo.
    
    Estos datos son ilustrativos, no reales.
    """
    data = []
    
    # Ejemplo: Vegueta - zona muy afectada
    for i in range(12):
        data.append({
            "barrio": "Vegueta",
            "tipo": "Vivienda Vacacional",
            "plazas": 4 + (i % 4) * 2,
            "registro": f"VT-35-{1000+i:04d}",
            "ano_registro": 2018 + (i % 6)
        })
    
    # Triana
    for i in range(8):
        data.append({
            "barrio": "Triana",
            "tipo": "Vivienda Vacacional",
            "plazas": 4 + (i % 3) * 2,
            "registro": f"VT-35-{2000+i:04d}",
            "ano_registro": 2019 + (i % 5)
        })
    
    # Playa de las Canteras
    for i in range(25):
        data.append({
            "barrio": "Playa de las Canteras",
            "tipo": "Apartamento Turístico" if i % 3 == 0 else "Vivienda Vacacional",
            "plazas": 2 + (i % 6) * 2,
            "registro": f"AT-35-{3000+i:04d}",
            "ano_registro": 2017 + (i % 7)
        })
    
    # Mesa y López
    for i in range(6):
        data.append({
            "barrio": "Mesa y López",
            "tipo": "Vivienda Vacacional",
            "plazas": 4 + (i % 3) * 2,
            "registro": f"VT-35-{4000+i:04d}",
            "ano_registro": 2020 + (i % 4)
        })
    
    # La Isleta
    for i in range(4):
        data.append({
            "barrio": "La Isleta",
            "tipo": "Vivienda Vacacional",
            "plazas": 4 + (i % 2) * 2,
            "registro": f"VT-35-{5000+i:04d}",
            "ano_registro": 2021 + (i % 3)
        })
    
    return pd.DataFrame(data)


def aggregate_by_barrio(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega datos de viviendas turísticas por barrio.
    
    Args:
        df: DataFrame con datos de viviendas
    
    Returns:
        DataFrame agregado con count y plazas por barrio
    """
    if df.empty:
        return df
    
    agg = df.groupby('barrio').agg(
        num_viviendas=('registro', 'count'),
        plazas_totales=('plazas', 'sum'),
        ano_primer_registro=('ano_registro', 'min'),
        ano_ultimo_registro=('ano_registro', 'max')
    ).reset_index()
    
    return agg
