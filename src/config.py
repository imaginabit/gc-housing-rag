"""Configuración del proyecto GC Housing RAG."""

import logging
import os
import warnings
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_PROCESSED_DIR = DATA_DIR / "processed"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
DATA_RAW_DIR.mkdir(exist_ok=True)
DATA_PROCESSED_DIR.mkdir(exist_ok=True)


def get_env(key: str, default: str = None, required: bool = False) -> str:
    """
    Obtiene una variable de entorno con advertencia si falta.

    Args:
        key: Nombre de la variable de entorno
        default: Valor por defecto si no existe
        required: Si True, lanza ValueError

    Returns:
        Valor de la variable o default
    """
    value = os.getenv(key, default)
    if required and not value:
        warnings.warn(
            f"La variable de entorno '{key}' no está configurada. "
            f"Algunas funcionalidades no estarán disponibles.",
            stacklevel=2,
        )
        return ""
    return value or ""


# Logging
LOG_LEVEL = get_env("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Crea un logger con el nombre dado."""
    return logging.getLogger(name)


# API Keys
GROQ_API_KEY = get_env("GROQ_API_KEY", required=True)
PINECONE_API_KEY = get_env("PINECONE_API_KEY", required=True)

# Pinecone
PINECONE_INDEX = get_env("PINECONE_INDEX", "gc-housing")
PINECONE_ENV = get_env("PINECONE_ENV", "us-east-1")

# CORS
ALLOWED_ORIGINS = get_env("ALLOWED_ORIGINS", "*").split(",")

# INE
INE_MUNICIPIO = get_env("INE_CODIGO_MUNICIPIO", "35020")  # Las Palmas de GC

# Embedding model (local, no requiere API key)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Barrios de Las Palmas de GC (13 barrios principales)
BARRIOS_LPGC = [
    "Vegueta",
    "Triana",
    "Mesa y López",
    "Playa de las Canteras",
    "La Isleta",
    "San Juan",
    "San Nicolás",
    "Alameda",
    "Cono Sur",
    "Tamaraceite",
    "La Paterca",
    "Tenoya",
    "Buena Vista",
]
