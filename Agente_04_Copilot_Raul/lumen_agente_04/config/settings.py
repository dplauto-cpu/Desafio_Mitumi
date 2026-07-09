"""
Carga de configuracion de Lumen desde .env (sin dependencias externas).
Si no existe .env (solo .env.example), se usan valores por defecto de modo demo.
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
            valor = valor.split("#", 1)[0].strip()  # quita comentarios en linea
            valores.setdefault(clave.strip(), valor)

    return valores


SETTINGS = cargar_env()
MODO_DEMO = SETTINGS.get("MODO_DEMO", "True") == "True"
LLM_PROVIDER = SETTINGS.get("LLM_PROVIDER", "")
LLM_MODEL = SETTINGS.get("LLM_MODEL", "")

# --- API real "Proyecto Tripulaciones" (ERP de Eventos, ver openapi.yaml) -------------------
# Cubre hoy solo eventos/clientes/espacios/ponentes (GET). Salas, presupuestos, estados y
# ponencias no tienen endpoint todavia y siguen leyendose de data/mock/*.json - ver la nota de
# modo hibrido en src/lectura_datos.py.
USAR_API_TRIPULACIONES = SETTINGS.get("USAR_API_TRIPULACIONES", "False") == "True"
API_TRIPULACIONES_BASE_URL = SETTINGS.get("BACKEND_BASE_URL", "http://localhost:3000/api/v1")
# Token de servicio (JWT) ya emitido por POST /auth/login - Lumen no hace el login el mismo,
# solo reutiliza un token de una cuenta de servicio configurada aqui.
API_TRIPULACIONES_TOKEN = SETTINGS.get("API_TRIPULACIONES_TOKEN", "")
