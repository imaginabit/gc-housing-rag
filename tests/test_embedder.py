"""Tests para el módulo embedder."""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np


class TestEmbedTexts:
    """Tests para embed_texts()."""

    def test_embed_texts_empty_list(self, mock_env):
        """Debe retornar lista vacía cuando no hay textos."""
        # Import inside test to ensure mock_env is active
        from src.rag.embedder import embed_texts

        result = embed_texts([])
        assert result == []

    def test_embed_texts_single_text(self, mock_env):
        """Debe retornar embedding para un solo texto."""
        from src.rag.embedder import embed_texts

        mock_embedding = np.zeros(384)
        with patch("src.rag.embedder._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([mock_embedding])
            mock_get_model.return_value = mock_model

            result = embed_texts(["hola mundo"])

            assert len(result) == 1
            assert isinstance(result[0], list)
            assert len(result[0]) == 384

    def test_embed_texts_multiple_texts(self, mock_env):
        """Debe retornar embeddings para múltiples textos."""
        from src.rag.embedder import embed_texts

        mock_embedding = np.zeros(384)
        with patch("src.rag.embedder._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([mock_embedding, mock_embedding])
            mock_get_model.return_value = mock_model

            result = embed_texts(["texto1", "texto2"])

            assert len(result) == 2
            assert all(len(emb) == 384 for emb in result)


class TestEmbedQuery:
    """Tests para embed_query()."""

    def test_embed_query_basic(self, mock_env):
        """Debe retornar embedding de dimensión correcta."""
        from src.rag.embedder import embed_query

        mock_embedding = np.zeros(384)
        with patch("src.rag.embedder._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([mock_embedding])
            mock_get_model.return_value = mock_model

            result = embed_query("¿Cuántas viviendas vacacionales hay?")

            assert isinstance(result, list)
            assert len(result) == 384

    def test_embed_query_empty_string(self, mock_env):
        """Debe retornar lista vacía para string vacío."""
        from src.rag.embedder import embed_query

        with patch("src.rag.embedder._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([])
            mock_get_model.return_value = mock_model

            result = embed_query("")

            assert result == []


class TestCheckEmbeddingDim:
    """Tests para check_embedding_dim()."""

    def test_check_embedding_dim_valid(self, mock_env):
        """Debe retornar True para embedding de dimensión correcta."""
        from src.rag.embedder import check_embedding_dim

        embedding = [0.0] * 384
        assert check_embedding_dim(embedding) is True

    def test_check_embedding_dim_invalid(self, mock_env):
        """Debe retornar False para embedding de dimensión incorrecta."""
        from src.rag.embedder import check_embedding_dim

        embedding = [0.0] * 100
        assert check_embedding_dim(embedding) is False
