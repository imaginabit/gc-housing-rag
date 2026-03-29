# Éxodo Vecinal — Guía de Despliegue

> **Última actualización:** 29 de marzo de 2026
> **Servidor:** OVH VPS vps2023-le-2

---

## URLs

| Entorno | URL |
|---------|-----|
| **Producción** | https://exodovecinal.imaginabit.com |
| **GitHub** | https://github.com/imaginabit/gc-housing-rag |

---

## Información del Servidor

| Campo | Valor |
|-------|-------|
| **Host** | `vps-e1a2922e.vps.ovh.net` |
| **IP** | `51.75.125.217` |
| **Usuario SSH** | `debian` |
| **SO** | Debian 12 (Bookworm) |
| **RAM** | 2 GB (500MB reservados para la app) |
| **Disco** | 40 GB SSD |
| **Swap** | 2 GB (`/swapfile`) |
| **Python** | 3.11.2 |
| **Nginx** | 1.22.1 |

### Conexión SSH

```bash
ssh debian@51.75.125.217
```

---

## Arquitectura

```
Internet → Nginx (80/443, SSL) → Uvicorn (:8000, FastAPI)
                                    ├── /health
                                    ├── /query (RAG chat)
                                    ├── /map-data
                                    ├── /turismo-points
                                    ├── /barrios-polygons
                                    ├── /news
                                    └── /* (frontend estático)
```

### Rutas en el servidor

| Ruta | Contenido |
|------|-----------|
| `/opt/exodovecinal/` | Código fuente (repo clonado) |
| `/opt/exodovecinal/venv/` | Python venv (1.5GB, PyTorch CPU) |
| `/opt/exodovecinal/data/raw/` | CSVs de datos (~12MB) |
| `/opt/exodovecinal/.env` | Variables de entorno (API keys) |
| `/etc/systemd/system/exodovecinal.service` | Systemd service |
| `/etc/nginx/sites-available/exodovecinal` | Nginx virtualhost |
| `/etc/letsencrypt/live/exodovecinal.imaginabit.com/` | Certificados SSL |

---

## Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Frontend (mapa + chat + noticias) |
| `/health` | GET | Health check (verifica dependencias) |
| `/query` | POST | RAG query (embed → Pinecone → Groq) |
| `/map-data` | GET | Datos agregados para el mapa |
| `/turismo-points` | GET | Puntos de viviendas turísticas |
| `/barrios-polygons` | GET | Polígonos GeoJSON de barrios |
| `/news` | GET | Artículos curados sobre vivienda vacacional |
| `/docs` | GET | Documentación OpenAPI (Swagger) |

---

## Gestión del Servicio

### Estado

```bash
ssh debian@51.75.125.217 "sudo systemctl status exodovecinal"
```

### Reiniciar

```bash
ssh debian@51.75.125.217 "sudo systemctl restart exodovecinal"
```

### Ver logs

```bash
ssh debian@51.75.125.217 "sudo journalctl -u exodovecinal -f"
```

### Ver RAM del servicio

```bash
ssh debian@51.75.125.217 "systemctl show exodovecinal --property=MemoryCurrent | numfmt --to=iec"
```

---

## Actualizar Código

### Opción 1: Script automático (recomendado)

```bash
ssh debian@51.75.125.217 "cd /opt/exodovecinal && bash deploy/update.sh"
```

El script hace:
1. `git pull` — descarga cambios
2. `pip install -r requirements.txt` — actualiza dependencias si cambiaron
3. `sudo systemctl restart exodovecinal` — reinicia servicio
4. Verifica que `/health` responde `ok`

### Opción 2: Manual

```bash
ssh debian@51.75.125.217
cd /opt/exodovecinal
git pull
source venv/bin/activate
pip install -r requirements.txt  # solo si cambió requirements.txt
sudo systemctl restart exodovecinal
curl -s http://localhost:8000/health | python3 -m json.tool
```

### Opción 3: Solo reiniciar (sin actualizar código)

```bash
ssh debian@51.75.125.217 "sudo systemctl restart exodovecinal"
```

---

## Actualizar Datos (CSVs)

Si cambian los archivos en `data/raw/`:

```bash
# Desde tu máquina local
rsync -avz data/raw/ debian@51.75.125.217:/opt/exodovecinal/data/raw/

# Reiniciar para que coja los nuevos datos
ssh debian@51.75.125.217 "sudo systemctl restart exodovecinal"
```

---

## Reindexar Pinecone

Si necesitas regenerar el índice de Pinecone con datos nuevos:

```bash
ssh debian@51.75.125.217
cd /opt/exodovecinal
source venv/bin/activate
python -m src.rag.pipeline
```

Esto:
1. Carga los CSVs de `data/raw/`
2. Genera 32 chunks (ISTAC + barrios + Doorstep)
3. Genera embeddings con sentence-transformers
4. Borra y recrea el índice en Pinecone

**Nota:** El primer uso descarga el modelo de embeddings (~90MB).

---

## Variables de Entorno

El archivo `/opt/exodovecinal/.env` contiene:

```
GROQ_API_KEY=...        # Groq LLM (chat)
PINECONE_API_KEY=...    # Pinecone (vector DB)
PINECONE_INDEX=gc-housing
PINECONE_ENV=us-east-1
```

Para editar:

```bash
ssh debian@51.75.125.217 "nano /opt/exodovecinal/.env"
ssh debian@51.75.125.217 "sudo systemctl restart exodovecinal"
```

---

## SSL/TLS

- **Certificado:** Let's Encrypt (gratuito)
- **Renovación:** Automática (certbot cron)
- **Expiración:** 27 de junio de 2026
- **Verificar:** `ssh debian@51.75.125.217 "sudo certbot certificates"`

### Renovar manualmente

```bash
ssh debian@51.75.125.217 "sudo certbot renew --dry-run"  # test
ssh debian@51.75.125.217 "sudo certbot renew"             # renovar
```

---

## Monitoreo

### RAM

```bash
ssh debian@51.75.125.217 "free -h"
```

Límites del servicio:
- **MemoryHigh:** 400MB (aviso)
- **MemoryMax:** 500MB (kill si supera)
- **Swap:** 2GB (respaldo si RAM se llena)

### Disco

```bash
ssh debian@51.75.125.217 "df -h /"
```

### Procesos

```bash
ssh debian@51.75.125.217 "ps aux --sort=-%mem | head -10"
```

### Load average

```bash
ssh debian@51.75.125.217 "uptime"
```

---

## Troubleshooting

### Servicio no arranca

```bash
ssh debian@51.75.125.217
sudo journalctl -u exodovecinal --no-pager -n 50
```

Causas comunes:
- Falta `.env` → copiar con `scp`
- Falta `data/` → copiar con `rsync`
- Error de import → revisar `requirements.txt`

### Error 502 Bad Gateway

```bash
ssh debian@51.75.125.217
sudo systemctl status exodovecinal  # ¿está corriendo?
sudo systemctl restart exodovecinal
sudo nginx -t && sudo systemctl reload nginx
```

### Servicio matado por OOM (Out of Memory)

```bash
ssh debian@51.75.125.217 "sudo journalctl -u exodovecinal --no-pager | grep -i 'killed\|oom'"
```

Solución: verificar que el swap está activo:
```bash
ssh debian@51.75.125.217 "free -h | grep Swap"
# Debe mostrar 2.0Gi
```

Si swap no está:
```bash
ssh debian@51.75.125.217 "sudo swapon /swapfile"
```

### SSL expirado

```bash
ssh debian@51.75.125.217 "sudo certbot renew"
ssh debian@51.75.125.217 "sudo systemctl reload nginx"
```

---

## Instalación desde Cero

Si necesitas reinstalar todo en un servidor nuevo:

```bash
# 1. Copiar scripts al servidor
scp -r deploy/ debian@51.75.125.217:/tmp/

# 2. Ejecutar setup
ssh debian@51.75.125.217 "bash /tmp/deploy/setup.sh"

# 3. Copiar .env y datos
scp .env debian@51.75.125.217:/opt/exodovecinal/
rsync -avz data/raw/ debian@51.75.125.217:/opt/exodovecinal/data/raw/

# 4. Arrancar
ssh debian@51.75.125.217 "sudo systemctl start exodovecinal"

# 5. SSL
ssh debian@51.75.125.217 "sudo certbot --nginx -d exodovecinal.imaginabit.com"
```

---

## Notas Importantes

- **No usar Docker/Kubernetes** en este VPS (demasiado pequeño, 2GB RAM)
- **PyTorch CPU-only** (800MB vs 1.2GB CUDA) — ya configurado en `requirements.txt`
- **Lazy loading** del modelo de embeddings (~340MB idle, sube a ~400MB en primera query)
- **MemoryMax=500M** protege contra OOM — si la app supera eso, systemd la mata (no el kernel)
- **El repo es público** en GitHub — no meter secrets en el código
