import requests
import pandas as pd
from io import StringIO
from pathlib import Path

url = 'https://datos.canarias.es/catalogos/general/dataset/9f4355a2-d086-4384-ba72-d8c99aa2d544/resource/8ff8cc43-c00b-4513-8f42-a5b961c579e1/download/establecimientos-extrahoteleros-de-tipologia-vivienda-vacacional-inscritos-en-el-registro-genera.csv'

print('Descargando viviendas turísticas de Canarias...')
r = requests.get(url, timeout=60)
df = pd.read_csv(StringIO(r.text), encoding='utf-8', sep=';', on_bad_lines='skip', low_memory=False)
print(f'✅ Total Canarias: {len(df)} registros')

# Filtrar solo Las Palmas de GC
lpgc = df[df['direccion_municipio_nombre'].str.contains('Las Palmas', na=False, case=False)].copy()
print(f'✅ LPGC: {len(lpgc)} registros')

# Limpiar y renombrar columnas
lpgc = lpgc.rename(columns={
    'direccion_municipio_nombre': 'municipio',
    'direccion_localidad_nombre': 'barrio',
    'plazas': 'plazas',
    'longitud': 'lng',
    'latitud': 'lat',
    'establecimiento_nombre_comercial': 'nombre',
    'direccion': 'direccion',
    'establecimiento_tipologia': 'tipo'
})

lpgc['barrio'] = lpgc['barrio'].fillna('Otro')
lpgc['lng'] = pd.to_numeric(lpgc['lng'], errors='coerce')
lpgc['lat'] = pd.to_numeric(lpgc['lat'], errors='coerce')
lpgc['plazas'] = pd.to_numeric(lpgc['plazas'], errors='coerce')

# Guardar raw
out = Path('data/raw')
out.mkdir(exist_ok=True)
lpgc.to_csv(out / 'turismo_lpgc_real.csv', index=False)
print(f'✅ Guardado raw: {len(lpgc)} registros')

# Aggregate by barrio
barrio_agg = lpgc.groupby('barrio').agg(
    num_viviendas=('establecimiento_id', 'count'),
    plazas_totales=('plazas', 'sum'),
    plazas_media=('plazas', 'mean'),
    con_coords=('lat', lambda x: (x != 0).sum())
).reset_index()
barrio_agg.columns = ['barrio', 'num_viviendas', 'plazas_totales', 'plazas_media', 'con_coords']
barrio_agg = barrio_agg[barrio_agg['num_viviendas'] >= 5]

print(f'\n📊 {len(barrio_agg)} barrios con 5+ viviendas:')
print(barrio_agg.sort_values('num_viviendas', ascending=False).to_string(index=False))

barrio_agg.to_csv(out / 'turismo_by_barrio_real.csv', index=False)
print(f'\n✅ Guardado agregado por barrio')
