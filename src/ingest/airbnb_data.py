"""
Script para descargar datos de Inside Airbnb para Gran Canaria.

Inside Airbnb es un proyecto que hace scrape público de listados de Airbnb.
URL: http://insideairbnb.com/

Datos disponibles:
- listings.csv: información de cada alojamiento
- reviews.csv: reseñas
- calendar.csv: disponibilidad

Uso:
    python -m src.ingest.airbnb_data
"""
import requests
import pandas as pd
import io
import gzip
from pathlib import Path
from datetime import datetime

# Inside Airbnb data para Canary Islands / Gran Canaria
INSIDE_AIRBNB_URL = "http://insideairbnb.com/inside-airbnb-data/"
DATA_URL = "http://data.insideairbnb.com/canary-islands/las-palmas-gran-canaria/2024-12-14/data/"


def get_listings_url() -> str:
    """
    Obtiene la URL del último dataset disponible.
    Inside Airbnb cambia las URLs con cada actualización.
    """
    # URLs conocidas de Inside Airbnb para Gran Canaria
    # Formato: http://data.insideairbnb.com/canary-islands/las-palmas-gran-canaria/{date}/data/listings.csv.gz
    base = "http://data.insideairbnb.com/canary-islands/las-palmas-gran-canaria"
    
    # Fechas conocidas - la más reciente primero
    dates = [
        "2025-03-10",
        "2024-12-14", 
        "2024-09-10",
        "2024-06-10",
        "2024-03-10",
    ]
    
    for date in dates:
        url = f"{base}/{date}/data/listings.csv.gz"
        print(f"  Probando: {url}")
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                print(f"    ✅ Encontrado: {date}")
                return url
        except:
            pass
    
    return None


def download_listings() -> pd.DataFrame:
    """
    Descarga el CSV de listados de Inside Airbnb.
    
    Returns:
        DataFrame con columnas: id, name, neighbourhood, latitude, longitude,
        room_type, price, reviews_per_month, etc.
    """
    print("\n📥 Descargando listados de Inside Airbnb...")
    
    url = "http://data.insideairbnb.com/canary-islands/las-palmas-gran-canaria/2024-12-14/data/listings.csv.gz"
    
    try:
        print(f"  URL: {url}")
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        
        # Descomprimir
        print(f"  Descomprimiendo {len(resp.content)} bytes...")
        df = pd.read_csv(
            io.BytesIO(resp.content),
            compression='gzip',
            low_memory=False
        )
        
        print(f"  ✅ {len(df)} listados descargados")
        return df
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return pd.DataFrame()


def process_listings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Procesa los listados para extraer información relevante.
    
    Returns:
        DataFrame procesado con: barrio, direccion, tipo, plazas, lat, lng, precio
    """
    if df.empty:
        return df
    
    print("\n🔧 Procesando listados...")
    
    # Columnas útiles de Inside Airbnb
    useful_cols = [
        'id', 'name', 'neighbourhood', 'neighbourhood_group',
        'latitude', 'longitude', 'room_type', 'price',
        'minimum_nights', 'number_of_reviews', 'reviews_per_month',
        'calculated_host_listings_count', 'availability_365'
    ]
    
    # Seleccionar solo columnas disponibles
    available = [c for c in useful_cols if c in df.columns]
    df = df[available].copy()
    
    # Limpiar precio (quitar $ y comas)
    if 'price' in df.columns:
        df['price'] = df['price'].astype(str).str.replace('$', '').str.replace(',', '')
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Mapear neighbourhood a barrio (neighbourhood son los barrios de LPGC)
    # Los nombres en Inside Airbnb suelen estar en español
    print(f"   Barrios encontrados: {df['neighbourhood'].nunique()}")
    print(f"   {df['neighbourhood'].value_counts().head(10).to_dict()}")
    
    return df


def aggregate_by_neighbourhood(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega listados por barrio.
    
    Returns:
        DataFrame con: barrio, num_listings, avg_price, avg_reviews
    """
    if df.empty or 'neighbourhood' not in df.columns:
        return pd.DataFrame()
    
    agg = df.groupby('neighbourhood').agg(
        num_listings=('id', 'count'),
        avg_price=('price', 'mean'),
        avg_reviews=('number_of_reviews', 'mean'),
        total_reviews=('number_of_reviews', 'sum'),
        avg_availability=('availability_365', 'mean')
    ).reset_index()
    
    agg.columns = ['barrio', 'num_listings', 'avg_price', 'avg_reviews', 'total_reviews', 'avg_availability']
    
    return agg


def main():
    from src.config import DATA_RAW_DIR
    
    print("\n" + "="*60)
    print("📦 DATOS DE INSIDE AIRBNB - GRAN CANARIA")
    print("="*60)
    
    # Descargar
    df = download_listings()
    
    if df.empty:
        print("\n❌ No se pudieron descargar los datos")
        print("\nAlternativa: descargar manualmente desde:")
        print("  1. Ve a http://insideairbnb.com/")
        print("  2. Busca 'Las Palmas, Gran Canaria'")
        print("  3. Descarga 'listings.csv'")
        print("  4. Guárdalo en data/raw/airbnb_listings.csv")
        return
    
    # Procesar
    df_processed = process_listings(df)
    
    # Guardar raw
    raw_path = DATA_RAW_DIR / "airbnb_listings.csv"
    df_processed.to_csv(raw_path, index=False)
    print(f"\n✅ Guardado: {raw_path}")
    
    # Guardar agregado por barrio
    agg = aggregate_by_neighbourhood(df_processed)
    agg_path = DATA_RAW_DIR / "airbnb_by_barrio.csv"
    agg.to_csv(agg_path, index=False)
    print(f"✅ Guardado: {agg_path}")
    
    print(f"\n📊 Resumen por barrio:")
    print(agg.to_string(index=False))


if __name__ == "__main__":
    main()
