"""
Carga de configuración de agente_operis desde .env (sin dependencias
externas — mismo patrón que Agente_04_Copilot_Raul/lumen_agente_04/config/settings.py).
Si no existe .env (solo .env.example), se usan los valores de .env.example.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def cargar_env(ruta_env: Path = None) -> dict:
    ruta_env = ruta_env or (BASE_DIR / ".env")
    valores = dict(os.environ)

    if not ruta_env.exists():
        ruta_env = BASE_DIR / ".env.example"

    if ruta_env.exists():
        for linea in ruta_env.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            valor = valor.split("#", 1)[0].strip()  # quita comentarios en línea
            valores.setdefault(clave.strip(), valor)

    return valores


SETTINGS = cargar_env()

# --- Motor de extracción ---
# "reglas" (gratis, determinista, por defecto) o "llm" (Groq).
MOTOR_POR_DEFECTO = SETTINGS.get("OPERIS_MOTOR", "reglas")

# --- LLM (Groq) ---
# openai/gpt-oss-120b: modelo recomendado por el propio Groq como
# reemplazo de llama-3.1-8b-instant / llama-3.3-70b-versatile, que Groq
# retira el 16/08/2026 (ver agente_alerta_roberto/vigil_build_brief.md).
GROQ_API_KEY = SETTINGS.get("GROQ_API_KEY", "")
GROQ_MODEL = SETTINGS.get("GROQ_MODEL", "openai/gpt-oss-120b")

NOMBRE_AGENTE = "agente_operis"
