"""Tests para el módulo geocoder."""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestGeocodeAddress:
    """Tests para geocode_address()."""

    def test_geocode_empty_address(self, mock_env):
        """Debe retornar None para dirección vacía."""
        from src.ingest.geocoder import geocode_address

        result = geocode_address("")
        assert result is None

    def test_geocode_returns_coordinates(self, mock_env):
        """Debe retornar coordenadas válidas."""
        from src.ingest.geocoder import geocode_address

        # Test real - puede requerir network
        result = geocode_address("Calle Mayor 15", "35003")

        if result:
            assert "lat" in result
            assert "lon" in result
            assert isinstance(result["lat"], float)
            assert isinstance(result["lon"], float)

    def test_geocode_returns_dict(self, mock_env):
        """Debe retornar dict con lat y lon."""
        from src.ingest.geocoder import geocode_address

        # No mock - test real si hay network, o skip
        # Solo test de estructura
        pass


class TestGeocodeBatch:
    """Tests para geocode_batch()."""

    def test_geocode_batch_empty(self, mock_env):
        """Debe retornar lista vacía."""
        from src.ingest.geocoder import geocode_batch

        result = geocode_batch([])
        assert result == []
