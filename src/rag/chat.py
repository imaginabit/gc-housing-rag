"""
Módulo de chat - Generación de respuestas con MiniMax LLM.

Usa los resultados de Pinecone (contexto) + MiniMax LLM para 
generar respuestas a preguntas del usuario.
"""
import httpx
from typing import List, Dict, Any, Optional
from ..config import MINIMAX_API_KEY, MINIMAX_BASE_URL


# Modelo de chat - usa tu plan MiniMax
CHAT_MODEL = "MiniMax-Text-01"


def build_prompt(context: List[Dict[str, Any]], question: str) -> str:
    """
    Construye el prompt para el LLM con el contexto recuperado.
    
    Args:
        context: Lista de resultados de Pinecone con sus metadatos
        question: Pregunta del usuario
    
    Returns:
        Prompt formateado para el LLM
    """
    # Formatear contexto
    context_parts = []
    for i, match in enumerate(context, 1):
        meta = match.get("metadata", {})
        source = meta.get("source", "desconocido")
        text = meta.get("text", "")
        barrio = meta.get("barrio", "")
        ano = meta.get("ano", "")
        
        context_parts.append(f"[{i}] {source} ({barrio}, {ano}): {text}")
    
    context_str = "\n".join(context_parts)
    
    prompt = f"""Eres un asistente especializado en el impacto de la turistificación en Las Palmas de Gran Canaria.
Respondes en español canario, de forma cercana pero informativa.

Información relevante del mapa de datos:
{context_str}

Pregunta del usuario: {question}

Responde de forma clara y útil. Si no tienes suficiente información en el contexto, dilo honestamente.
Incluye datos específicos cuando estén disponibles (números, porcentajes, años).
"""
    
    return prompt


def ask_question(
    question: str,
    context: List[Dict[str, Any]],
    history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Genera una respuesta a la pregunta del usuario usando MiniMax LLM.
    
    Args:
        question: Pregunta del usuario
        context: Resultados de la búsqueda en Pinecone (contexto)
        history: Historial de conversación (opcional, para memoria)
    
    Returns:
        Respuesta generada por el LLM
    """
    url = f"{MINIMAX_BASE_URL}/text/chatcompletion_v2"
    
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Construir mensajes
    system_msg = """Eres un asistente especializado en el impacto de la turistificación en Las Palmas de Gran Canaria.
Respondes en español canario, de forma cercana pero informativa.
Das datos específicos cuando los tienes (números, porcentajes, años).
Si no tienes información suficiente, lo dices honestamente."""
    
    messages = [{"role": "system", "content": system_msg}]
    
    # Añadir historial si existe
    if history:
        for msg in history[-5:]:  # Últimos 5 mensajes
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Construir prompt con contexto
    prompt = build_prompt(context, question)
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": CHAT_MODEL,
        "messages": messages,
        "temperature": 0.3,  # RAG - baja temperatura para datos
        "max_tokens": 1024
    }
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # Extraer respuesta
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "Sin respuesta")
        
        return "Error: respuesta vacía del modelo"


def format_map_context(context: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Formatea el contexto de Pinecone para usarlo en el mapa interactivo.
    
    Args:
        context: Resultados de Pinecone
    
    Returns:
        Dict formateado para el frontend con datos geográficos
    """
    result = {
        "barrios": [],
        "data_points": []
    }
    
    seen_barrios = set()
    
    for match in context:
        meta = match.get("metadata", {})
        barrio = meta.get("barrio", "")
        score = match.get("score", 0)
        
        if barrio and barrio not in seen_barrios:
            seen_barrios.add(barrio)
            result["barrios"].append({
                "name": barrio,
                "score": score,
                "data": meta
            })
    
    return result
