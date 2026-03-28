"""Tests para el módulo API."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests para el endpoint GET /health."""

    def test_health_returns_ok(self, mock_env):
        """El endpoint /health debe retornar status 'ok'."""
        # Import here to ensure mock_env is active
        from src.rag.api import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "gc-housing-rag"

    def test_health_response_structure(self, mock_env):
        """El response debe tener los campos correctos."""
        from src.rag.api import app

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "service" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["service"], str)
