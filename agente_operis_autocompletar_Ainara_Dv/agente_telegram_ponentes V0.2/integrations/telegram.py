import requests

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_POLLING_TIMEOUT, TELEGRAM_REQUEST_TIMEOUT
from config.permisos import ALLOW_SEND_TELEGRAM

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else None

BOTONES_MENU_PONENTE = [
    ["✈️ Vuelo", "🏨 Hotel"],
    ["🚕 Taxi", "🕒 Horario"],
    ["📍 Lugar", "📄 Documentación"],
    ["📞 Contactar MITUMI", "🚨 Urgencia"],
]


def leer_updates(offset: int | None = None) -> list[dict]:
    if not BASE_URL:
        return []

    params = {"timeout": TELEGRAM_POLLING_TIMEOUT}
    if offset is not None:
        params["offset"] = offset

    r = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=TELEGRAM_REQUEST_TIMEOUT)
    data = r.json()
    return data.get("result", []) if data.get("ok") else []


def enviar_mensaje(chat_id: str | int, texto: str) -> dict:
    if not ALLOW_SEND_TELEGRAM:
        return {"ok": True, "modo": "envio_desactivado"}

    if not BASE_URL:
        return {"ok": False, "error": "telegram_token_no_configurado"}

    payload = {"chat_id": chat_id, "text": texto}
    r = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=TELEGRAM_REQUEST_TIMEOUT)
    return r.json()


def enviar_mensaje_con_botones(chat_id: str | int, texto: str) -> dict:
    """Envía mensaje con teclado visual persistente para el ponente.

    Se usa ReplyKeyboardMarkup porque es más sencillo para MVP:
    al pulsar un botón, Telegram envía el texto del botón como mensaje normal.
    """
    if not ALLOW_SEND_TELEGRAM:
        return {"ok": True, "modo": "envio_desactivado"}

    if not BASE_URL:
        return {"ok": False, "error": "telegram_token_no_configurado"}

    payload = {
        "chat_id": chat_id,
        "text": texto,
        "reply_markup": {
            "keyboard": BOTONES_MENU_PONENTE,
            "resize_keyboard": True,
            "one_time_keyboard": False,
            "input_field_placeholder": "Escribe tu consulta o usa los botones...",
        },
    }
    r = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=TELEGRAM_REQUEST_TIMEOUT)
    return r.json()


def update_a_payload(update: dict) -> dict | None:
    """Convierte un update de Telegram al contrato común de entrada del agente."""
    mensaje = update.get("message") or update.get("edited_message")
    if not mensaje:
        return None

    usuario = mensaje.get("from", {})
    chat = mensaje.get("chat", {})

    return {
        "id_evento": None,
        "id_registro": None,
        "tipo_peticion": "responder_consulta_ponente_telegram",
        "origen": "telegram",
        "usuario_solicitante": str(usuario.get("id")),
        "rol_usuario": "ponente",
        "datos": {
            "telegram_update_id": update.get("update_id"),
            "telegram_message_id": mensaje.get("message_id"),
            "telegram_user_id": str(usuario.get("id")),
            "telegram_chat_id": chat.get("id"),
            "nombre_usuario": usuario.get("first_name"),
            "texto": mensaje.get("text", ""),
        },
        "contexto": {
            "fase_evento": "ponentes",
            "canal": "telegram",
        },
        "modo": "ejecucion_controlada",
    }


def extraer_texto_respuesta(resultado_agente: dict) -> str | None:
    """Extrae el texto de respuesta desde el contrato común de salida."""
    for borrador in resultado_agente.get("borradores_generados", []):
        if borrador.get("canal") == "telegram":
            return borrador.get("texto")
    return None
