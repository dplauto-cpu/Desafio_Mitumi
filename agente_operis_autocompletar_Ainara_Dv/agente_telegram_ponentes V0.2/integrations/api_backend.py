import json
import requests
from config.fuentes import MOCK_DIR
from config.settings import BACKEND_ENABLED, BACKEND_BASE_URL, BACKEND_API_KEY, BACKEND_TIMEOUT_SECONDS
from config.permisos import ALLOW_BACKEND_READ, ALLOW_BACKEND_WRITE


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if BACKEND_API_KEY:
        headers["Authorization"] = f"Bearer {BACKEND_API_KEY}"
    return headers


def _leer_mock(nombre: str):
    ruta = MOCK_DIR / nombre
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


def obtener_ponente_por_telegram(telegram_user_id: str) -> dict | None:
    if not ALLOW_BACKEND_READ:
        return None

    if BACKEND_ENABLED:
        url = f"{BACKEND_BASE_URL}/api/ponentes/by-telegram/{telegram_user_id}"
        r = requests.get(url, headers=_headers(), timeout=BACKEND_TIMEOUT_SECONDS)
        return r.json() if r.status_code == 200 else None

    for ponente in _leer_mock("ponentes.json"):
        if str(ponente.get("telegram_user_id")) == str(telegram_user_id):
            return ponente
    return None


def obtener_eventos_activos_ponente(id_ponente: int) -> list[dict]:
    if not ALLOW_BACKEND_READ:
        return []

    if BACKEND_ENABLED:
        url = f"{BACKEND_BASE_URL}/api/ponentes/{id_ponente}/eventos-activos"
        r = requests.get(url, headers=_headers(), timeout=BACKEND_TIMEOUT_SECONDS)
        return r.json() if r.status_code == 200 else []

    eventos = _leer_mock("eventos_ponente.json")
    return [e for e in eventos if e.get("id_ponente") == id_ponente and e.get("estado") == "activo"]


def obtener_info_ponente_evento(id_ponente: int, id_evento: int) -> dict | None:
    if not ALLOW_BACKEND_READ:
        return None

    if BACKEND_ENABLED:
        url = f"{BACKEND_BASE_URL}/api/eventos/{id_evento}/ponentes/{id_ponente}"
        r = requests.get(url, headers=_headers(), timeout=BACKEND_TIMEOUT_SECONDS)
        return r.json() if r.status_code == 200 else None

    registros = _leer_mock("ponente_evento.json")
    for registro in registros:
        if registro.get("id_ponente") == id_ponente and registro.get("id_evento") == id_evento:
            return registro
    return None


def registrar_comunicacion(payload: dict) -> dict:
    if not ALLOW_BACKEND_WRITE:
        return {"ok": True, "modo": "mock_sin_escritura", "registrado": False}

    if BACKEND_ENABLED:
        url = f"{BACKEND_BASE_URL}/api/comunicaciones"
        r = requests.post(url, headers=_headers(), json=payload, timeout=BACKEND_TIMEOUT_SECONDS)
        return {"ok": r.status_code in [200, 201], "status_code": r.status_code}

    return {"ok": True, "modo": "mock", "registrado": True}


def crear_incidencia(payload: dict) -> dict:
    if not ALLOW_BACKEND_WRITE:
        return {"ok": True, "modo": "mock_sin_escritura", "creada": False}

    if BACKEND_ENABLED:
        url = f"{BACKEND_BASE_URL}/api/incidencias"
        r = requests.post(url, headers=_headers(), json=payload, timeout=BACKEND_TIMEOUT_SECONDS)
        return {"ok": r.status_code in [200, 201], "status_code": r.status_code}

    return {"ok": True, "modo": "mock", "creada": True}
