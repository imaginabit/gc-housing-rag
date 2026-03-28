import requests
import re
import json
import pandas as pd
from pathlib import Path

url = 'https://doorstepanalytics.com/report?location=Gran_Canaria&country=Spain'
print('Descargando datos de Doorstep Analytics...')
r = requests.get(url, timeout=30)
text = r.text

# Extract stats
stats = re.findall(r'>([A-Za-z\s]+?)</div>\s*<div[^>]*>\s*([\d,]+)', text)
stats_dict = {label.strip(): int(num.replace(',', '')) for label, num in stats}

# Total listings
match = re.search(r'Total listings:[\s,]*([\d,]+)', text)
total = int(match.group(1).replace(',', '')) if match else 0

# Last updated
match = re.search(r'Last Updated: (\d{4}-\d{2}-\d{2})', text)
updated = match.group(1) if match else 'unknown'

# Bedroom breakdown
bed_matches = re.findall(r'>(\d+)\s*<.*?Bed Homes', text)
bed_1 = int(bed_matches[0].replace(',', '')) if len(bed_matches) > 0 else 0
bed_2 = int(bed_matches[1].replace(',', '')) if len(bed_matches) > 1 else 0
bed_3 = int(bed_matches[2].replace(',', '')) if len(bed_matches) > 2 else 0

print(f'Total listings: {total}')
print(f'Updated: {updated}')
print(f'Stats: {stats_dict}')

# Extract heatmap coordinates
match = re.search(r'var heatMapData = \[(.*?)\];', text, re.DOTALL)
coords = []
if match:
    data_str = '[' + match.group(1) + ']'
    try:
        coords = json.loads(data_str)
    except:
        coords = re.findall(r'\{"lat":\s*([-\d.]+),\s*"lng":\s*([-\d.]+)\}', data_str)
        coords = [{'lat': float(c[0]), 'lng': float(c[1])} for c in coords]

print(f'Coordinates: {len(coords)} points')

# Save
out = Path('data/raw')
out.mkdir(exist_ok=True)

# Stats
df_stats = pd.DataFrame([{
    'total_listings': total,
    'entire_homes': stats_dict.get('Entire Homes', 0),
    'private_rooms': stats_dict.get('Private Rooms', 0),
    'serviced_apartments': stats_dict.get('Serviced Apartments', 0),
    'shared_rooms': stats_dict.get('Shared Rooms', 0),
    'bed_1': bed_1,
    'bed_2': bed_2,
    'bed_3': bed_3,
    'last_updated': updated,
}])
df_stats.to_csv(out / 'doorstep_stats.csv', index=False)

# Coordinates (all Gran Canaria)
df_coords = pd.DataFrame(coords)
df_coords.to_csv(out / 'doorstep_coordinates.csv', index=False)

print(f'\n✅ Guardado: doorstep_stats.csv ({len(df_stats)} rows)')
print(f'✅ Guardado: doorstep_coordinates.csv ({len(df_coords)} rows)')
