"""Pytest configuration and shared fixtures."""

import pytest
import os


@pytest.fixture
def mock_env(monkeypatch):
    """
    Fixture que provee variables de entorno necesarias para tests.
    """
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("PINECONE_API_KEY", "test-pinecone-key")
    monkeypatch.setenv("PINECONE_INDEX", "test-index")
    monkeypatch.setenv("PINECONE_ENV", "us-east-1")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:3000")
    return monkeypatch
