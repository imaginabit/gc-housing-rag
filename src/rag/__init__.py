"""Módulo RAG."""

from .embedder import embed_texts, embed_query
from .indexer import index_data, query_index
from .chat import ask_question

__all__ = ["embed_texts", "embed_query", "index_data", "query_index", "ask_question"]
