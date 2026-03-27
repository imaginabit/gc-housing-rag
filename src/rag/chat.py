"""
Módulo de chat - Generación de respuestas con Groq LLM (gratis, rápido).

Usa los resultados de Pinecone (contexto) + Groq LLM para
generar respuestas a preguntas del usuario.

Modelos disponibles en Groq (gratis):
- llama-3.3-70b-versatile (recomendado)
- llama-3.1-8b-instant
- mixtral-8x7b-32768
"""
import groq
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

# Groq client
groq_client = groq.Groq(api_key=os.getenv("GROQ_API_KEY", ""))

# Modelo de chat
CHAT_MODEL = "llama-3.3-70b-versatile"


SYSTEM_PROMPT = """Eres un asistente especializado en el impacto de la turistificación en Las Palmas de Gran Canaria.
Respondes en español canario, de forma cercana pero informativa.
Das datos específicos cuando los tienes (números, porcentajes, años).
Si no tienes información suficiente, lo dices honestamente."""


def build_prompt(context: List[Dict[str, Any]], question: str) -> str:
    """
    Construye el prompt para el LLM con el contexto recuperado.
    NO incluye HTML en la respuesta del LLM.
    """
    context_parts = []
    for i, match in enumerate(context, 1):
        meta = match.get("metadata", {})
        source = meta.get("source", "desconocido")
        text = meta.get("text", "")
        barrio = meta.get("barrio", "")
        ano = meta.get("ano", "")

        context_parts.append(f"[{i}] {source} ({barrio}, {ano}): {text}")

    context_str = "\n".join(context_parts)

    prompt = f"""Información relevante del mapa de datos:
{context_str}

Pregunta del usuario: {question}

Responde en TEXTO PLANO, sin ningún formato HTML ni Markdown.
No uses etiquetas como <div>, <strong>, <br>, etc.
Solo texto plano con saltos de línea normales.
Si no tienes suficiente información en el contexto, dilo honestamente.
Incluye datos específicos cuando estén disponibles (números, porcentajes, años)."""

    return prompt


def ask_question(
    question: str,
    context: List[Dict[str, Any]],
    history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Genera una respuesta a la pregunta del usuario usando Groq LLM.
    """
    # Construir mensajes
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Añadir historial si existe
    if history:
        for msg in history[-5:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    # Construir prompt con contexto
    prompt = build_prompt(context, question)
    messages.append({"role": "user", "content": prompt})

    try:
        response = groq_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=1024
        )

        return response.choices[0].message.content

    except groq.APIError as e:
        return f"Error de API Groq: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


def format_map_context(context: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Formatea el contexto de Pinecone para usarlo en el mapa interactivo.
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
