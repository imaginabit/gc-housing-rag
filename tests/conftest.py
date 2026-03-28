"""Pytest configuration and shared fixtures."""

import pytest
import os


@pytest.fixture
def mock_env(monkeypatch):
    """
    Fixture que provee variables de entorno necesarias para tests.

    Uso:
        def test_something(mock_env):
            # Las variables GROQ_API_KEY, MINIMAX_API_KEY, PINECONE_API_KEY
            # están disponibles en os.environ
            ...
    """
    # Variables requeridas por config.py
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("MINIMAX_API_KEY", "test-minimax-key")
    monkeypatch.setenv("PINECONE_API_KEY", "test-pinecone-key")
    # Variables opcionales
    monkeypatch.setenv("PINECONE_INDEX", "test-index")
    monkeypatch.setenv("PINECONE_ENV", "test-env")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:3000")
    return monkeypatch
