import requests
import pandas as pd
from io import StringIO
from pathlib import Path

out = Path('data/raw')
out.mkdir(exist_ok=True)

url = 'https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00065A_000061/1.11.csv'
print('Descargando ISTAC viviendas vacacionales...')
r = requests.get(url, timeout=60)
df = pd.read_csv(StringIO(r.text), sep=',', encoding='utf-8', low_memory=False)
df.columns = ['territorio', 'codigo', 'periodo', 'periodo_code',
              'intervalo_plazas', 'intervalo_plazas_code', 'medida',
              'medida_code', 'valor', 'notas', 'confidencial', 'estado']

# Save full raw
df.to_csv(out / 'istac_viviendas_vacacionales_full.csv', index=False)
print(f'✅ Full raw guardado: {len(df)} filas')

# Filter LPGC only
lpgc = df[df['territorio'] == 'Las Palmas de Gran Canaria'].copy()
lpgc.to_csv(out / 'istac_viviendas_lpgc.csv', index=False)
print(f'✅ LPGC guardado: {len(lpgc)} filas')

# Pivot: periodo x medida (Total plazas only)
lpgc_total = lpgc[lpgc['intervalo_plazas'] == 'Total'].copy()
lpgc_total['valor'] = pd.to_numeric(lpgc_total['valor'], errors='coerce')
pivot = lpgc_total.pivot_table(
    index='periodo',
    columns='medida',
    values='valor'
).reset_index()
pivot.to_csv(out / 'istac_viviendas_lpgc_pivot.csv', index=False)
print(f'✅ Pivot guardado: {len(pivot)} meses')

print(f'\n📊 Últimos 6 meses LPGC:')
print(pivot.tail(6).to_string(index=False))

# Also download the turismo vacacional equivalent dataset URL
print('\n📊 Descargando AIRBTICS data...')
airbtics_url = 'https://airbtics.com/annual-airbnb-revenue-in-las-palmas-de-gran-canaria-las-palmas-spain-es'
print(f'  (Manual: {airbtics_url})')
print('  Para datos automáticos de Airbnb, usar insideairbnb.com/get-the-data/')
