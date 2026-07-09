import os
from pathlib import Path
from dotenv import load_dotenv

# Raíz del agente: src/agents/agente_telegram_ponentes/
AGENT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(AGENT_ROOT / ".env")


def _bool(nombre: str, defecto: str = "false") -> bool:
    return os.getenv(nombre, defecto).strip().lower() in {"true", "1", "yes", "si", "sí"}


# ============================================================
# AGENTE / ENTORNO
# ============================================================
AGENT_NAME = os.getenv("AGENT_NAME", "agente_telegram_ponentes")
APP_ENV = os.getenv("APP_ENV", "local")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Madrid")
MODO_DEMO = _bool("MODO_DEMO", "true")
ORQUESTADOR_ENABLED = _bool("ORQUESTADOR_ENABLED", "false")

# ============================================================
# LLM
# ============================================================
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1200"))
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

# ============================================================
# TELEGRAM
# ============================================================
TELEGRAM_ENABLED = _bool("TELEGRAM_ENABLED", "false")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_POLLING_TIMEOUT = int(os.getenv("TELEGRAM_POLLING_TIMEOUT", "5"))
TELEGRAM_REQUEST_TIMEOUT = int(os.getenv("TELEGRAM_REQUEST_TIMEOUT", "15"))
TELEGRAM_CHECK_SECONDS = int(os.getenv("TELEGRAM_CHECK_SECONDS", "15"))

# ============================================================
# BACKEND
# ============================================================
BACKEND_ENABLED = _bool("BACKEND_ENABLED", "false")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY")
BACKEND_TIMEOUT_SECONDS = int(os.getenv("BACKEND_TIMEOUT_SECONDS", "15"))

# ============================================================
# SERVICIO LOCAL
# ============================================================
ORDINARY_START_HOUR = int(os.getenv("ORDINARY_START_HOUR", "7"))
ORDINARY_END_HOUR = int(os.getenv("ORDINARY_END_HOUR", "23"))
SERVICE_LOOP_SECONDS = int(os.getenv("SERVICE_LOOP_SECONDS", "2"))
QUIET_MODE_ENABLED = _bool("QUIET_MODE_ENABLED", "true")
ALLOW_OUT_OF_HOURS_LOGGING = _bool("ALLOW_OUT_OF_HOURS_LOGGING", "true")


# ============================================================
# ESCALADO HUMANO
# ============================================================
ADMIN_TELEGRAM_CHAT_ID = os.getenv("ADMIN_TELEGRAM_CHAT_ID")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
MIN_CONFIDENCE_TO_REPLY = float(os.getenv("MIN_CONFIDENCE_TO_REPLY", "0.75"))

# ============================================================
# RAG / LOGS
# ============================================================
RAG_ENABLED = _bool("RAG_ENABLED", "false")
RAG_RESULTS = int(os.getenv("RAG_RESULTS", "3"))
RAG_MIN_SIMILARITY = float(os.getenv("RAG_MIN_SIMILARITY", "0.20"))

DATA_DIR = os.getenv("DATA_DIR", "data")
RAG_DIR = os.getenv("RAG_DIR", "data/rag")
OUTPUTS_DIR = os.getenv("OUTPUTS_DIR", "outputs")
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SHOW_STEPS = _bool("SHOW_STEPS", "true")
SAVE_CONVERSATION_LOG = _bool("SAVE_CONVERSATION_LOG", "true")
