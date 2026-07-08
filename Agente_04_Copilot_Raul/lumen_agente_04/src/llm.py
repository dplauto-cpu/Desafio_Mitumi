"""
Cliente del LLM para Lumen (Agente 04 - Copilot).

Motor confirmado: Groq (API compatible con OpenAI). La API key y el modelo se leen SIEMPRE
desde config/settings.py (que a su vez los carga de .env) - nunca se hardcodean aqui, para poder
rotar la key o cambiar de proveedor sin tocar codigo.

Limites del plan gratuito de Groq (tokens por dia, TPD):
  llama-3.3-70b-versatile  -> 100.000 TPD  (mas capaz, limite mas bajo)
  llama-3.1-8b-instant     -> 500.000 TPD  (mas rapido, limite 5x mayor)
  gemma2-9b-it             -> 500.000 TPD  (alternativa)
Con volumen alto de consultas, cambiar LLM_MODEL en .env a llama-3.1-8b-instant.
"""

from openai import OpenAI

from config.settings import SETTINGS

GROQ_API_KEY = SETTINGS.get("GROQ_API_KEY", "")
GROQ_BASE_URL = SETTINGS.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
MODELO = SETTINGS.get("LLM_MODEL", "llama-3.3-70b-versatile")
TEMPERATURA = float(SETTINGS.get("LLM_TEMPERATURE", "0.1") or 0.1)
MAX_TOKENS = int(SETTINGS.get("LLM_MAX_TOKENS", "800") or 800)

_cliente = None


def llm_disponible() -> bool:
    """True si hay una API key configurada en .env (no vacia y no el placeholder de ejemplo)."""
    return bool(GROQ_API_KEY) and "poner_api_key" not in GROQ_API_KEY


def _obtener_cliente() -> OpenAI:
    global _cliente
    if _cliente is None:
        if not llm_disponible():
            raise RuntimeError("GROQ_API_KEY no configurada en .env - LLM no disponible.")
        _cliente = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    return _cliente


def llamar_llm(prompt_sistema: str, mensaje_usuario: str) -> str:
    """
    Llama al LLM configurado (Groq) con un prompt de sistema y un mensaje de usuario.
    Devuelve el texto de la respuesta (se espera JSON, segun el formato de prompts/).

    Quien llama a esta funcion DEBE capturar excepciones y hacer fallback a las reglas
    deterministas de src/agente.py - Lumen nunca debe quedarse sin responder porque el LLM
    falle o no este configurado.
    """
    cliente = _obtener_cliente()
    respuesta = cliente.chat.completions.create(
        model=MODELO,
        temperature=TEMPERATURA,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": mensaje_usuario},
        ],
    )
    return respuesta.choices[0].message.content
