"""Configuración del proyecto GC Housing RAG."""

import os
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


def require_env(key: str) -> str:
    """
    Obtiene una variable de entorno requerida.

    Args:
        key: Nombre de la variable de entorno

    Returns:
        Valor de la variable

    Raises:
        ValueError: Si la variable no está definida
    """
    value = os.getenv(key)
    if not value:
        raise ValueError(
            f"La variable de entorno '{key}' es requerida. Configura tu .env"
        )
    return value


# Required API Keys (validadas con require_env)
GROQ_API_KEY = require_env("GROQ_API_KEY")
MINIMAX_API_KEY = require_env("MINIMAX_API_KEY")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")

# Pinecone (requerido)
PINECONE_API_KEY = require_env("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "gc-housing")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1")

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# INE
INE_MUNICIPIO = os.getenv("INE_CODIGO_MUNICIPIO", "35020")  # Las Palmas de GC

# Embedding model
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
