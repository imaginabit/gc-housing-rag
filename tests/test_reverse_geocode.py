"""Tests para el módulo reverse_geocode."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestReverseGeocode:
    """Tests para reverse_geocode()."""

    def test_reverse_geocode_valid_point(self, mock_env):
        """Debe retornar barrio para punto válido."""
        from src.ingest.reverse_geocode import reverse_geocode

        # Punto en Vegueta
        result = reverse_geocode(28.099, -15.420)
        assert result == "VEGUETA"

    def test_reverse_geocode_triana(self, mock_env):
        """Punto en Triana."""
        from src.ingest.reverse_geocode import reverse_geocode

        result = reverse_geocode(28.105, -15.417)
        assert result == "TRIANA"

    def test_reverse_geocode_canteras(self, mock_env):
        """Punto en Santa Catalina - Canteras."""
        from src.ingest.reverse_geocode import reverse_geocode

        result = reverse_geocode(28.140, -15.430)
        assert result == "SANTA CATALINA - CANTERAS"

    def test_reverse_geocode_zero_coords(self, mock_env):
        """Debe retornar None para coordenadas 0,0."""
        from src.ingest.reverse_geocode import reverse_geocode

        result = reverse_geocode(0.0, 0.0)
        assert result is None

    def test_reverse_geocode_out_of_range(self, mock_env):
        """Debe retornar None para coords fuera de rango."""
        from src.ingest.reverse_geocode import reverse_geocode

        # Fuera de Gran Canaria
        result = reverse_geocode(40.0, -3.0)  # Madrid
        assert result is None

    def test_reverse_geocode_guanarteme(self, mock_env):
        """Punto en Guanarteme."""
        from src.ingest.reverse_geocode import reverse_geocode

        result = reverse_geocode(28.130, -15.445)
        assert result == "GUANARTEME"


class TestLoadBarrios:
    """Tests para load_barrios()."""

    def test_load_barrios_returns_list(self, mock_env):
        """Debe retornar lista de features."""
        from src.ingest.reverse_geocode import load_barrios

        result = load_barrios()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_load_barrios_has_nombre(self, mock_env):
        """Cada feature debe tener nombre de barrio."""
        from src.ingest.reverse_geocode import load_barrios

        features = load_barrios()
        for f in features[:5]:
            props = f.get("properties", {})
            assert "NUCL_DS_NOMBRE" in props


class TestGetBarrioPolygons:
    """Tests para get_barrio_polygons()."""

    def test_returns_dict(self, mock_env):
        """Debe retornar dict de polígonos."""
        from src.ingest.reverse_geocode import get_barrio_polygons

        polygons = get_barrio_polygons()
        assert isinstance(polygons, dict)
        assert len(polygons) > 0

    def test_contains_vegueta(self, mock_env):
        """Debe contener Vegueta."""
        from src.ingest.reverse_geocode import get_barrio_polygons

        polygons = get_barrio_polygons()
        assert "VEGUETA" in polygons
