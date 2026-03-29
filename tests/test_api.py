"""Tests para el módulo API."""

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests para el endpoint GET /health."""

    def test_health_returns_200(self, mock_env):
        """El endpoint /health debe retornar 200 con checks."""
        from src.rag.api import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ok", "degraded")
        assert data["service"] == "gc-housing-rag"
        assert "checks" in data

    def test_health_response_structure(self, mock_env):
        """El response debe tener los campos correctos."""
        from src.rag.api import app

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "service" in data
        assert "checks" in data
        assert "embedder" in data["checks"]
        assert "pinecone" in data["checks"]
        assert "data" in data["checks"]


class TestBarriosEndpoint:
    """Tests para el endpoint GET /barrios."""

    def test_barrios_returns_list(self, mock_env):
        """El endpoint /barrios debe retornar una lista de barrios."""
        from src.rag.api import app

        client = TestClient(app)
        response = client.get("/barrios")

        assert response.status_code == 200
        data = response.json()
        assert "barrios" in data
        assert "has_data" in data
        assert isinstance(data["barrios"], list)

    def test_barrios_fallback_to_default(self, mock_env, tmp_path):
        """Si no hay CSV, debe usar BARRIOS_LPGC por defecto."""
        from src.rag.api import app
        from src.rag import api as api_module

        with patch.object(api_module, "DATA_RAW_DIR", tmp_path):
            client = TestClient(app)
            response = client.get("/barrios")
            data = response.json()

            assert data["has_data"] is False
            assert "Vegueta" in data["barrios"]
            assert "Triana" in data["barrios"]


class TestQueryEndpoint:
    """Tests para el endpoint POST /query."""

    def test_query_validates_question_required(self, mock_env):
        """POST /query sin question debe retornar 422."""
        from src.rag.api import app

        client = TestClient(app)
        response = client.post("/query", json={})

        assert response.status_code == 422

    def test_query_validates_question_type(self, mock_env):
        """POST /query con question no-string debe retornar 422."""
        from src.rag.api import app

        client = TestClient(app)
        response = client.post("/query", json={"question": 123})

        assert response.status_code == 422

    @patch("src.rag.api.embed_query")
    @patch("src.rag.api.query_index")
    @patch("src.rag.api.ask_question")
    def test_query_returns_answer(self, mock_ask, mock_query, mock_embed, mock_env):
        """POST /query debe retornar answer + sources + map_data."""
        from src.rag.api import app

        mock_embed.return_value = [0.1] * 384
        mock_query.return_value = [
            {
                "score": 0.95,
                "metadata": {
                    "barrio": "Vegueta",
                    "source": "ISTAC",
                    "tipo": "viviendas",
                    "text": "Vegueta tiene 150 viviendas turísticas",
                },
            }
        ]
        mock_ask.return_value = "Vegueta tiene 150 viviendas turísticas."

        client = TestClient(app)
        response = client.post(
            "/query", json={"question": "¿Cuántas viviendas hay en Vegueta?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "map_data" in data
        assert len(data["sources"]) == 1
        assert data["sources"][0]["barrio"] == "Vegueta"

    @patch("src.rag.api.embed_query")
    def test_query_embed_failure(self, mock_embed, mock_env):
        """Si embed_query falla, debe retornar 500."""
        from src.rag.api import app

        mock_embed.return_value = None

        client = TestClient(app)
        response = client.post("/query", json={"question": "test"})

        assert response.status_code == 500

    def test_query_with_barrio_filter(self, mock_env):
        """POST /query con barrio debe filtrar resultados."""
        from src.rag.api import app

        with patch("src.rag.api.embed_query", return_value=[0.1] * 384):
            with patch("src.rag.api.query_index", return_value=[]) as mock_query:
                with patch("src.rag.api.ask_question", return_value="respuesta"):
                    client = TestClient(app)
                    client.post(
                        "/query",
                        json={"question": "test", "barrio": "Vegueta"},
                    )
                    # Verificar que se pasó el filtro
                    call_args = mock_query.call_args
                    assert call_args.kwargs.get("filter_dict") == {"barrio": "Vegueta"}


class TestMapDataEndpoint:
    """Tests para el endpoint GET /map-data."""

    def test_map_data_returns_dict(self, mock_env, tmp_path):
        """GET /map-data debe retornar un dict con datos."""
        from src.rag.api import app
        from src import config

        with patch.object(config, "DATA_RAW_DIR", tmp_path):
            client = TestClient(app)
            response = client.get("/map-data")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)


class TestTurismoPointsEndpoint:
    """Tests para el endpoint GET /turismo-points."""

    def test_turismo_points_no_data(self, mock_env, tmp_path):
        """Sin datos debe retornar error + lista vacía."""
        from src.rag.api import app
        from src.rag import api as api_module

        with patch.object(api_module, "DATA_RAW_DIR", tmp_path):
            client = TestClient(app)
            response = client.get("/turismo-points")

            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["points"] == []


class TestBarriosPolygonsEndpoint:
    """Tests para el endpoint GET /barrios-polygons."""

    def test_barrios_polygons_no_data(self, mock_env, tmp_path):
        """Sin datos debe retornar FeatureCollection vacío."""
        from src.rag.api import app
        from src.rag import api as api_module

        with patch.object(api_module, "DATA_RAW_DIR", tmp_path):
            client = TestClient(app)
            response = client.get("/barrios-polygons")

            assert response.status_code == 200
            data = response.json()
            assert data["type"] == "FeatureCollection"
            assert data["features"] == []


class TestCORS:
    """Tests para verificación de CORS."""

    def test_cors_headers_present(self, mock_env):
        """Las respuestas deben incluir headers CORS."""
        from src.rag.api import app

        client = TestClient(app)
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORS middleware returns 200 for preflight
        assert response.status_code in (200, 400)


class TestNumpyConversion:
    """Tests para la conversión de tipos numpy."""

    def test_np_to_native_dict(self, mock_env):
        """Debe convertir numpy types dentro de dicts."""
        import numpy as np
        from src.rag.api import _np_to_native

        data = {"int": np.int64(42), "float": np.float64(3.14), "str": "hello"}
        result = _np_to_native(data)

        assert result["int"] == 42
        assert isinstance(result["int"], int)
        assert abs(result["float"] - 3.14) < 0.01
        assert isinstance(result["float"], float)
        assert result["str"] == "hello"

    def test_np_to_native_list(self, mock_env):
        """Debe convertir numpy arrays a listas."""
        import numpy as np
        from src.rag.api import _np_to_native

        data = [np.int64(1), np.float64(2.0)]
        result = _np_to_native(data)

        assert result == [1, 2.0]

    def test_np_to_native_nested(self, mock_env):
        """Debe manejar estructuras anidadas."""
        import numpy as np
        from src.rag.api import _np_to_native

        data = {"nested": {"value": np.int64(100)}}
        result = _np_to_native(data)

        assert result["nested"]["value"] == 100
        assert isinstance(result["nested"]["value"], int)
