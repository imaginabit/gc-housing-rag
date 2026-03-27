"""Pipeline principal de indexación RAG.

Coordina la ingestión de datos, generación de chunks,
embeddings e indexación en Pinecone.
"""
import pandas as pd
import unicodedata
import re
from pathlib import Path
from typing import List, Dict, Any

from ..config import DATA_RAW_DIR, DATA_PROCESSED_DIR, EMBEDDING_DIM
from ..ingest import fetch_ine_population, fetch_turismo_data
from .embedder import embed_texts, embed_query
from .indexer import index_data, create_index_if_not_exists


def slugify(text: str) -> str:
    """Convierte texto a ID ASCII seguro (sin acentos, sin espacios)."""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-zA-Z0-9_]', '_', text)
    return text.lower()


def load_processed_data() -> Dict[str, pd.DataFrame]:
    """
    Carga los datos procesados de INE y turismo.
    """
    ine_path = DATA_RAW_DIR / "ine_population_processed.csv"
    turismo_path = DATA_RAW_DIR / "turismo_viviendas.csv"
    
    data = {}
    
    if ine_path.exists():
        data["ine"] = pd.read_csv(ine_path)
        print(f"  📊 INE: {len(data['ine'])} registros")
    else:
        print("  ⚠ No hay datos del INE. Ejecuta primero la ingestión.")
    
    if turismo_path.exists():
        data["turismo"] = pd.read_csv(turismo_path)
        print(f"  🏠 Turismo: {len(data['turismo'])} registros")
    else:
        print("  ⚠ No hay datos de turismo. Ejecuta primero la ingestión.")
    
    return data


def create_chunks(data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """
    Crea chunks de texto para indexar en Pinecone.
    
    Cada chunk es un documento con:
    - id: identificador único
    - text: texto para embedding
    - metadata: año, barrio, tipo, fuente...
    """
    chunks = []
    chunk_id = 0
    
    # Barriios principales de LPGC
    BARRIOS = [
        "Vegueta", "Triana", "Mesa y López", "Playa de las Canteras",
        "La Isleta", "San Juan", "San Nicolás", "Alameda", "Cono Sur",
        "Tamaraceite", "La Paterca", "Tenoya", "Buena Vista"
    ]
    
    # Chunks de INE (población)
    if "ine" in data:
        df = data["ine"]
        for barrio in BARRIOS:
            barrio_data = df[df['barrio'] == barrio]
            if barrio_data.empty:
                continue
            
            # Evolución de población del barrio
            pop_by_year = barrio_data.groupby('ano')['poblacion'].sum().to_dict()
            
            if pop_by_year:
                anos = sorted(pop_by_year.keys())
                pob_primero = pop_by_year.get(anos[0], 0)
                pob_ultimo = pop_by_year.get(anos[-1], 0)
                cambio_pct = ((pob_ultimo - pob_primero) / pob_primero * 100) if pob_primero > 0 else 0
                
                text = (
                    f"En el barrio de {barrio}, según datos del INE, "
                    f"la población era de {pob_primero:,} habitantes en {anos[0]} "
                    f"y de {pob_ultimo:,} en {anos[-1]}. "
                    f"Esto representa un cambio del {cambio_pct:+.1f}% en el período {anos[0]}-{anos[-1]}. "
                    f"Actualmente hay {pob_ultimo:,} habitantes."
                )
                
                chunks.append({
                    "id": f"ine_{slugify(barrio)}",
                    "text": text,
                    "metadata": {
                        "source": "INE - Padrón de habitantes",
                        "barrio": barrio,
                        "tipo": "poblacion",
                        "ano_inicio": anos[0],
                        "ano_fin": anos[-1],
                        "poblacion_inicio": int(pob_primero),
                        "poblacion_fin": int(pob_ultimo),
                        "cambio_pct": round(cambio_pct, 1),
                        "text": text  # Guardar el texto en metadata para poder mostrarlo
                    }
                })
                chunk_id += 1
    
    # Chunks de turismo (viviendas turísticas)
    if "turismo" in data:
        df = data["turismo"]
        for barrio in BARRIOS:
            barrio_data = df[df['barrio'] == barrio]
            if barrio_data.empty:
                continue
            
            num_viviendas = len(barrio_data)
            plazas_totales = barrio_data['plazas'].sum()
            primer_ano = barrio_data['ano_registro'].min()
            ultimo_ano = barrio_data['ano_registro'].max()
            num_tipos = barrio_data['tipo'].nunique()
            
            text = (
                f"En el barrio de {barrio}, según el Registro de Turismo de Canarias, "
                f"hay {num_viviendas} viviendas turísticas registradas "
                f"con un total de {plazas_totales} plazas. "
                f"El primer registro data de {primer_ano} y el más reciente de {ultimo_ano}. "
                f"Hay {num_tipos} tipos diferentes de alojamiento turístico en este barrio."
            )
            
            chunks.append({
                "id": f"turismo_{slugify(barrio)}",
                "text": text,
                "metadata": {
                    "source": "Registro de Turismo de Canarias",
                    "barrio": barrio,
                    "tipo": "turismo",
                    "num_viviendas": num_viviendas,
                    "plazas_totales": int(plazas_totales),
                    "ano_primer_registro": int(primer_ano),
                    "ano_ultimo_registro": int(ultimo_ano),
                    "text": text
                }
            })
            chunk_id += 1
    
    # Chunks comparativos (población vs turismo)
    if "ine" in data and "turismo" in data:
        for barrio in BARRIOS:
            ine_data = data["ine"][data["ine"]["barrio"] == barrio]
            tur_data = data["turismo"][data["turismo"]["barrio"] == barrio]
            
            if ine_data.empty or tur_data.empty:
                continue
            
            # Población actual
            latest_ine = ine_data[ine_data['ano'] == ine_data['ano'].max()]
            pob_actual = latest_ine['poblacion'].sum() if not latest_ine.empty else 0
            
            # Viviendas turísticas
            num_vt = len(tur_data)
            plazas_vt = tur_data['plazas'].sum()
            
            # Ratio plazas turísticas vs habitantes
            ratio = (plazas_vt / pob_actual * 100) if pob_actual > 0 else 0
            
            text = (
                f"En {barrio}, el ratio de plazas turísticas por cada 100 habitantes es "
                f"de {ratio:.1f}. Con {pob_actual:,} habitantes y {plazas_vt:,} plazas turísticas, "
                f"esto significa que por cada 100 residentes hay {ratio:.1f} plazas destinadas a turismo. "
                f"Un ratio alto indica mayor presión turística sobre el barrio."
            )
            
            chunks.append({
                "id": f"ratio_{slugify(barrio)}",
                "text": text,
                "metadata": {
                    "source": "Análisis comparativo INE + Registro Turismo",
                    "barrio": barrio,
                    "tipo": "ratio",
                    "poblacion": int(pob_actual),
                    "plazas_turisticas": int(plazas_vt),
                    "ratio_por_100": round(ratio, 1),
                    "text": text
                }
            })
            chunk_id += 1
    
    # Chunk general de contexto sobre turistificación en LPGC
    chunks.append({
        "id": "contexto_general",
        "text": (
            "Las Palmas de Gran Canaria es la capital de la isla de Gran Canaria, "
            "con aproximadamente 380,000 habitantes. En los últimos años, el turismo "
            "de apartamentos y viviendas vacacionales ha crecido significativamente, "
            "especialmente en los barrios del centro histórico (Vegueta), Triana, "
            "y la franja costera de Playa de las Canteras. "
            "Este crecimiento ha generado preocupación entre los vecinos por el aumento "
            "de los alquileres, la pérdida de residentes en barrios históricos, "
            "y el impacto en el comercio de proximidad."
        ),
        "metadata": {
            "source": "Contexto general",
            "barrio": "Las Palmas GC",
            "tipo": "contexto",
            "text": "Contexto general sobre LPGC"
        }
    })
    chunk_id += 1
    
    print(f"\n  📝 Generados {len(chunks)} chunks para indexar")
    return chunks


def generate_embeddings(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Genera embeddings para todos los chunks de texto.
    
    Args:
        chunks: Lista de chunks con campo 'text'
    
    Returns:
        Lista de chunks con campo 'embedding' añadido
    """
    print(f"\n  🤖 Generando embeddings con MiniMax ({len(chunks)} chunks)...")
    
    texts = [chunk["text"] for chunk in chunks]
    
    # Batch embeddings
    batch_size = 20
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        print(f"  ... procesando {min(i+batch_size, len(texts))}/{len(texts)}")
        
        embeddings = embed_texts(batch)
        all_embeddings.extend(embeddings)
    
    # Añadir embeddings a chunks
    for chunk, embedding in zip(chunks, all_embeddings):
        chunk["embedding"] = embedding
    
    # Verificar dimensiones
    if all_embeddings and len(all_embeddings[0]) == EMBEDDING_DIM:
        print(f"  ✅ Embeddings OK ({EMBEDDING_DIM} dim)")
    else:
        print(f"  ⚠️ Dimensión inesperada: {len(all_embeddings[0]) if all_embeddings else 0}")
    
    return chunks


def run_index_pipeline():
    """
    Ejecuta el pipeline completo de indexación:
    1. Cargar datos
    2. Crear chunks
    3. Generar embeddings
    4. Indexar en Pinecone
    """
    print("\n" + "="*60)
    print("🏗️  PIPELINE DE INDEXACIÓN RAG - GC Housing")
    print("="*60)
    
    # 1. Cargar datos
    print("\n[1/4] Cargando datos...")
    data = load_processed_data()
    
    if not data:
        print("  ❌ No hay datos. Ejecuta la ingestión primero.")
        return
    
    # 2. Crear chunks
    print("\n[2/4] Creando chunks de texto...")
    chunks = create_chunks(data)
    
    # 3. Generar embeddings
    print("\n[3/4] Generando embeddings...")
    chunks = generate_embeddings(chunks)
    
    # 4. Indexar en Pinecone
    print("\n[4/4] Indexando en Pinecone...")
    index_data(chunks)
    
    print("\n" + "="*60)
    print("✅ INDEXACIÓN COMPLETA")
    print("="*60)


if __name__ == "__main__":
    run_index_pipeline()
