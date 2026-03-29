#!/bin/bash
# ============================================
# Éxodo Vecinal — Update Script
# ============================================
# Ejecutar en el servidor: bash update.sh
# Actualiza código, deps y reinicia servicio

set -e

echo "=========================================="
echo "  Éxodo Vecinal — Actualizar"
echo "=========================================="

cd /opt/exodovecinal

# 1. Pull últimos cambios
echo ""
echo "[1/3] Descargando cambios..."
git pull

# 2. Actualizar dependencias (solo si cambió requirements.txt)
echo "[2/3] Actualizando dependencias..."
source venv/bin/activate
pip install -r requirements.txt -q

# 3. Reiniciar servicio
echo "[3/3] Reiniciando servicio..."
sudo systemctl restart exodovecinal

# Verificar
sleep 2
STATUS=$(curl -s http://localhost:8000/health | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))")
if [ "$STATUS" = "ok" ]; then
    echo ""
    echo "✅ Actualización completada — servicio OK"
else
    echo ""
    echo "⚠️  Servicio responde: $STATUS — revisar logs:"
    echo "   sudo journalctl -u exodovecinal -f"
fi
