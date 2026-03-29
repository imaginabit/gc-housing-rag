"""Tests para el módulo de configuración."""

import pytest
import warnings


class TestGetEnv:
    """Tests para la función get_env."""

    def test_get_env_returns_value(self, mock_env):
        """Debe retornar el valor si existe."""
        from src.config import get_env

        result = get_env("GROQ_API_KEY")
        assert result == "test-groq-key"

    def test_get_env_returns_default(self, mock_env):
        """Debe retornar default si no existe."""
        from src.config import get_env

        result = get_env("NONEXISTENT_VAR", "default-value")
        assert result == "default-value"

    def test_get_env_required_warns(self, monkeypatch):
        """Si required=True y la var no existe, debe advertir."""
        monkeypatch.delenv("MISSING_VAR", raising=False)
        from src.config import get_env

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = get_env("MISSING_VAR", required=True)

            assert result == ""
            assert len(w) == 1
            assert "MISSING_VAR" in str(w[0].message)


class TestConfigValues:
    """Tests para los valores de configuración."""

    def test_embedding_model_is_sentence_transformers(self, mock_env):
        """El modelo de embeddings debe ser sentence-transformers."""
        from src.config import EMBEDDING_MODEL

        assert "sentence-transformers" in EMBEDDING_MODEL
        assert "MiniLM" in EMBEDDING_MODEL

    def test_embedding_dim_is_384(self, mock_env):
        """La dimensión de embeddings debe ser 384."""
        from src.config import EMBEDDING_DIM

        assert EMBEDDING_DIM == 384

    def test_barrios_lpgc_has_13(self, mock_env):
        """Debe haber 13 barrios principales."""
        from src.config import BARRIOS_LPGC

        assert len(BARRIOS_LPGC) == 13
        assert "Vegueta" in BARRIOS_LPGC
        assert "Triana" in BARRIOS_LPGC

    def test_no_minimax_in_config(self, mock_env):
        """No debe existir MINIMAX_API_KEY en config."""
        import src.config as config

        assert not hasattr(config, "MINIMAX_API_KEY")


class TestConfigPaths:
    """Tests para los paths de configuración."""

    def test_data_dirs_exist(self, mock_env):
        """Los directorios de datos deben existir."""
        from src.config import DATA_DIR, DATA_RAW_DIR, DATA_PROCESSED_DIR

        assert DATA_DIR.exists()
        assert DATA_RAW_DIR.exists()
        assert DATA_PROCESSED_DIR.exists()

    def test_project_root_is_parent_of_src(self, mock_env):
        """PROJECT_ROOT debe ser el directorio padre de src/."""
        from src.config import PROJECT_ROOT

        assert (PROJECT_ROOT / "src").exists()
