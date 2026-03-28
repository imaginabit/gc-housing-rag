"""Tests para el módulo real_chunks."""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock


class TestLoadRealData:
    """Tests para load_real_data()."""

    def test_load_real_data_empty_dir(self, mock_env, tmp_path):
        """Debe retornar dict vacío cuando no hay datos."""
        from src.rag.real_chunks import load_real_data

        with patch("src.rag.real_chunks.DATA_RAW_DIR", tmp_path):
            result = load_real_data()
            assert result == {}

    def test_load_real_data_with_csv(self, mock_env, tmp_path):
        """Debe cargar archivos CSV cuando existen."""
        from src.rag.real_chunks import load_real_data

        # Create mock ISTAC file
        istac_file = tmp_path / "istac_viviendas_lpgc_pivot.csv"
        istac_file.write_text(
            "periodo,Plazas disponibles,Viviendas vacacionales disponibles\n"
            "01/2024,1000,300\n"
            "02/2024,1100,310\n"
        )

        with patch("src.rag.real_chunks.DATA_RAW_DIR", tmp_path):
            result = load_real_data()
            assert "istac" in result
            assert len(result["istac"]) == 2


class TestCreateContextChunk:
    """Tests para create_context_chunk()."""

    def test_create_context_chunk_returns_list(self, mock_env):
        """Debe retornar una lista con un chunk."""
        from src.rag.real_chunks import create_context_chunk

        result = create_context_chunk()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_create_context_chunk_structure(self, mock_env):
        """El chunk debe tener los campos requeridos."""
        from src.rag.real_chunks import create_context_chunk

        result = create_context_chunk()
        chunk = result[0]

        assert "id" in chunk
        assert "text" in chunk
        assert "metadata" in chunk
        assert chunk["id"] == "contexto_general"
        assert "source" in chunk["metadata"]


class TestSlugify:
    """Tests para slugify() en pipeline.py."""

    def test_slugify_basic(self, mock_env):
        """Convierte texto a slug."""
        from src.rag.pipeline import slugify

        assert slugify("Hola Mundo") == "hola_mundo"
        assert slugify("Vegueta") == "vegueta"

    def test_slugify_accented(self, mock_env):
        """Elimina acentos."""
        from src.rag.pipeline import slugify

        assert slugify("Las Palmas") == "las_palmas"
        assert slugify("España") == "espana"

    def test_slugify_special_chars(self, mock_env):
        """Reemplaza caracteres especiales."""
        from src.rag.pipeline import slugify

        assert slugify("Test @#$%") == "test_____"
