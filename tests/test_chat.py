"""Tests para el módulo chat."""

import pytest
from unittest.mock import patch, MagicMock


class TestBuildPrompt:
    """Tests para build_prompt()."""

    def test_build_prompt_basic(self, mock_env):
        """Construye prompt con contexto básico."""
        from src.rag.chat import build_prompt

        context = [
            {
                "metadata": {
                    "source": "ISTAC",
                    "barrio": "Vegueta",
                    "text": "Datos de prueba",
                }
            }
        ]
        question = "¿Cuántas viviendas hay?"

        result = build_prompt(context, question)

        assert "ISTAC" in result
        assert "Vegueta" in result
        assert "Datos de prueba" in result
        assert "¿Cuántas viviendas hay?" in result

    def test_build_prompt_multiple_contexts(self, mock_env):
        """Múltiples fuentes en el prompt."""
        from src.rag.chat import build_prompt

        context = [
            {"metadata": {"source": "ISTAC", "barrio": "Vegueta", "text": "Texto 1"}},
            {"metadata": {"source": "INE", "barrio": "Triana", "text": "Texto 2"}},
        ]
        question = "¿Qué pasa?"

        result = build_prompt(context, question)

        assert "[1]" in result
        assert "[2]" in result


class TestFormatMapContext:
    """Tests para format_map_context()."""

    def test_format_map_context_empty(self, mock_env):
        """Retorna estructura vacía."""
        from src.rag.chat import format_map_context

        result = format_map_context([])
        assert result == {"barrios": [], "data_points": []}

    def test_format_map_context_with_data(self, mock_env):
        """Formatea contextos con barrios."""
        from src.rag.chat import format_map_context

        context = [
            {
                "metadata": {"barrio": "Vegueta", "source": "ISTAC"},
                "score": 0.9,
            },
            {
                "metadata": {"barrio": "Triana", "source": "INE"},
                "score": 0.8,
            },
        ]

        result = format_map_context(context)

        assert len(result["barrios"]) == 2
        assert result["barrios"][0]["name"] == "Vegueta"
        assert result["barrios"][1]["name"] == "Triana"

    def test_format_map_context_duplicates(self, mock_env):
        """Evita duplicados de barrio."""
        from src.rag.chat import format_map_context

        context = [
            {"metadata": {"barrio": "Vegueta"}, "score": 0.9},
            {"metadata": {"barrio": "Vegueta"}, "score": 0.8},
        ]

        result = format_map_context(context)
        assert len(result["barrios"]) == 1


class TestAskQuestion:
    """Tests para ask_question()."""

    def test_ask_question_success(self, mock_env):
        """Retorna respuesta del LLM."""
        from src.rag.chat import ask_question

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Respuesta de prueba"

        context = [{"metadata": {"text": "Contexto"}}]

        with patch("src.rag.chat.groq_client") as mock_groq:
            mock_groq.chat.completions.create.return_value = mock_response

            result = ask_question("Pregunta?", context)

            assert result == "Respuesta de prueba"

    def test_ask_question_api_error(self, mock_env):
        """Maneja errores de API."""
        from src.rag.chat import ask_question

        context = [{"metadata": {"text": "Contexto"}}]

        with patch("src.rag.chat.groq_client") as mock_groq:
            mock_groq.chat.completions.create.side_effect = Exception("API Error")

            result = ask_question("Pregunta?", context)

            assert "Error" in result
