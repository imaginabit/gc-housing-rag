#!/bin/bash
# ============================================
# Éxodo Vecinal — Actualizar Noticias
# ============================================
# Ejecutar diariamente vía cron:
#   0 6 * * * cd /opt/exodovecinal && bash deploy/update_news.sh >> /var/log/exodovecinal_news.log 2>&1
#
# Hace:
#   1. Ejecuta el scraper de Google News RSS
#   2. Guarda artículos en data/raw/news_articles.json
#   3. No necesita reiniciar el servicio (lee el archivo en cada request)

set -e

cd /opt/exodovecinal
source venv/bin/activate

echo "=== $(date) — Actualizando noticias ==="
python3 -m src.ingest.news_scraper

TOTAL=$(python3 -c "import json; print(json.load(open('data/raw/news_articles.json'))['total'])")
echo "✅ ${TOTAL} artículos actualizados"
