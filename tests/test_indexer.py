"""Tests para el módulo indexer."""

import pytest
from unittest.mock import patch, MagicMock, call


class TestGetPineconeClient:
    """Tests para get_pinecone_client()."""

    def test_get_pinecone_client_returns_instance(self, mock_env):
        """Debe retornar instancia de Pinecone."""
        from src.rag.indexer import get_pinecone_client

        with patch("src.rag.indexer.Pinecone") as mock_pinecone:
            mock_pinecone.return_value = MagicMock()
            result = get_pinecone_client()
            assert result is not None


class TestQueryIndex:
    """Tests para query_index()."""

    def test_query_index_returns_matches(self, mock_env):
        """Debe retornar los matches de Pinecone."""
        from src.rag.indexer import query_index

        mock_embedding = [0.1] * 384
        mock_matches = [
            {
                "id": "test_1",
                "score": 0.9,
                "metadata": {"text": "test", "barrio": "Vegueta"},
            }
        ]

        with patch("src.rag.indexer.get_pinecone_client") as mock_get_client:
            mock_client = MagicMock()
            mock_index = MagicMock()
            mock_index.query.return_value = {"matches": mock_matches}
            mock_client.Index.return_value = mock_index
            mock_get_client.return_value = mock_client

            result = query_index(mock_embedding, top_k=5)

            assert result == mock_matches
            mock_index.query.assert_called_once()


class TestDeleteAll:
    """Tests para delete_all()."""

    def test_delete_all_calls_pinecone(self, mock_env):
        """Debe llamar a delete con delete_all=True."""
        from src.rag.indexer import delete_all

        with patch("src.rag.indexer.get_pinecone_client") as mock_get_client:
            mock_client = MagicMock()
            mock_index = MagicMock()
            mock_client.Index.return_value = mock_index
            mock_get_client.return_value = mock_client

            delete_all()

            mock_index.delete.assert_called_once_with(delete_all=True)
