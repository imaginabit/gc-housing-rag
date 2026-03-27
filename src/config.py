"""Configuración del proyecto GC Housing RAG."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_PROCESSED_DIR = DATA_DIR / "processed"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
DATA_RAW_DIR.mkdir(exist_ok=True)
DATA_PROCESSED_DIR.mkdir(exist_ok=True)

# API Keys
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")

# Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "gc-housing")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1")

# INE
INE_MUNICIPIO = os.getenv("INE_CODIGO_MUNICIPIO", "35020")  # Las Palmas de GC

# Embedding model
EMBEDDING_MODEL = "embo-01"
EMBEDDING_DIM = 1536  # MiniMax embedding dimension
