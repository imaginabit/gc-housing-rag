"""Módulo de ingestión de datos."""

from .ine import fetch_ine_population
from .turismo import fetch_turismo_data

__all__ = ["fetch_ine_population", "fetch_turismo_data"]
