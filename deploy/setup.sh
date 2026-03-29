#!/bin/bash
# ============================================
# Éxodo Vecinal — Setup Script (1 vez)
# ============================================
# Ejecutar como: bash setup.sh
# Requiere: sudo access, git, internet

set -e

echo "=========================================="
echo "  Éxodo Vecinal — Setup en VPS"
echo "=========================================="

# 1. Actualizar sistema
echo ""
echo "[1/9] Actualizando sistema..."
sudo apt update -qq

# 2. Instalar dependencias del sistema
echo "[2/9] Instalando Python y dependencias..."
sudo apt install -y -qq python3 python3-venv python3-pip git nginx certbot python3-certbot-nginx

# 3. Crear swap file (protección RAM)
echo "[3/9] Configurando swap file (2GB)..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "  ✅ Swap creado y activado"
else
    echo "  ⏭️  Swap ya existe"
fi

# 4. Clonar repositorio
echo "[4/9] Clonando repositorio..."
if [ ! -d /opt/exodovecinal ]; then
    sudo git clone https://github.com/tu-usuario/gc-housing-rag.git /opt/exodovecinal
    sudo chown -R debian:debian /opt/exodovecinal
else
    echo "  ⏭️  Directorio ya existe, actualizando..."
    cd /opt/exodovecinal && git pull
fi

# 5. Crear venv e instalar dependencias
echo "[5/9] Instalando dependencias Python (esto tarda ~5 min)..."
cd /opt/exodovecinal
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  ✅ Dependencias instaladas"

# 6. Crear directorios necesarios
echo "[6/9] Creando directorios..."
mkdir -p data/raw data/processed

# 7. Instalar systemd service
echo "[7/9] Instalando servicio systemd..."
sudo cp deploy/exodovecinal.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable exodovecinal

# 8. Configurar nginx
echo "[8/9] Configurando nginx..."
sudo cp deploy/nginx-exodovecinal.conf /etc/nginx/sites-available/exodovecinal
sudo ln -sf /etc/nginx/sites-available/exodovecinal /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
echo "  ✅ Nginx configurado"

# 9. Instrucciones finales
echo ""
echo "=========================================="
echo "  ✅ SETUP COMPLETADO"
echo "=========================================="
echo ""
echo "Próximos pasos manuales:"
echo ""
echo "  1. Subir .env:"
echo "     scp .env debian@$(hostname -I | awk '{print $1}'):/opt/exodovecinal/"
echo ""
echo "  2. Subir datos:"
echo "     scp -r data/raw/ debian@$(hostname -I | awk '{print $1}'):/opt/exodovecinal/data/"
echo ""
echo "  3. Arrancar servicio:"
echo "     sudo systemctl start exodovecinal"
echo ""
echo "  4. Verificar:"
echo "     curl http://localhost:8000/health"
echo ""
echo "  5. Configurar DNS en GoDaddy:"
echo "     A record: exodovecinal → $(hostname -I | awk '{print $1}')"
echo ""
echo "  6. SSL (después de DNS):"
echo "     sudo certbot --nginx -d exodovecinal.imaginabit.com"
echo ""
