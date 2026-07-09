import json
import os
import time
from pathlib import Path

from config.settings import (
    TELEGRAM_ENABLED,
    TELEGRAM_CHECK_SECONDS,
    SERVICE_LOOP_SECONDS,
    SHOW_STEPS,
    ADMIN_TELEGRAM_CHAT_ID,
)
from config.permisos import ALLOW_SEND_TELEGRAM, ALLOW_NOTIFY_ADMIN
from src.agente import ejecutar_agente
from integrations.telegram import (
    leer_updates,
    enviar_mensaje,
    enviar_mensaje_con_botones,
    update_a_payload,
    extraer_texto_respuesta,
)


AGENT_ROOT = Path(__file__).resolve().parent

BOTON_URGENCIA = "🚨 Urgencia"
BOTON_CONTACTAR = "📞 Contactar MITUMI"
COMANDOS_BIENVENIDA = {"/start", "start", "menu", "/menu", "ayuda", "/ayuda"}
BOTONES_NORMALIZADOS = {
    "✈️ vuelo": "Consulta de botón: datos de vuelo y viaje del ponente.",
    "✈ vuelo": "Consulta de botón: datos de vuelo y viaje del ponente.",
    "🏨 hotel": "Consulta de botón: datos de hotel y alojamiento del ponente.",
    "🚕 taxi": "Consulta de botón: datos de taxi y traslados del ponente.",
    "🕒 horario": "Consulta de botón: horario de ponencia del ponente.",
    "📍 lugar": "Consulta de botón: lugar, dirección y sala de la ponencia.",
    "📄 documentación": "Consulta de botón: documentación pendiente del ponente.",
    "📄 documentacion": "Consulta de botón: documentación pendiente del ponente.",
}


def _normalizar_id(valor) -> str:
    return str(valor).strip() if valor is not None else ""


def _normalizar_texto(valor: str | None) -> str:
    return (valor or "").strip().lower()


def obtener_admin_chat_id() -> str:
    """
    Variable principal: ADMIN_TELEGRAM_CHAT_ID.
    Se acepta TELEGRAM_ADMIN_CHAT_ID como alias por compatibilidad con pruebas anteriores.
    """
    return _normalizar_id(ADMIN_TELEGRAM_CHAT_ID or os.getenv("TELEGRAM_ADMIN_CHAT_ID"))


def cargar_contacto_ponente_desde_mock(telegram_user_id: str) -> dict:
    """
    En fase local sin backend/BD, lee datos de contacto desde data/mock/ponentes.json.
    En integración real, esta información vendrá del backend/BD.
    """
    ruta = AGENT_ROOT / "data" / "mock" / "ponentes.json"
    if not ruta.exists():
        return {}

    try:
        ponentes = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return {}

    for ponente in ponentes:
        if _normalizar_id(ponente.get("telegram_user_id")) == _normalizar_id(telegram_user_id):
            return ponente

    return {}


def cargar_evento_principal_ponente_desde_mock(telegram_user_id: str) -> dict:
    """Devuelve el primer evento asociado al ponente en los datos mock."""
    ponente = cargar_contacto_ponente_desde_mock(telegram_user_id)
    id_ponente = ponente.get("id_ponente")
    if id_ponente is None:
        return {}

    ruta = AGENT_ROOT / "data" / "mock" / "ponente_evento.json"
    if not ruta.exists():
        return {}

    try:
        registros = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return {}

    for registro in registros:
        if registro.get("id_ponente") == id_ponente:
            return registro

    return {}


def construir_mensaje_bienvenida(payload: dict) -> str:
    datos = payload.get("datos", {}) or {}
    telegram_user_id = _normalizar_id(datos.get("telegram_user_id"))
    contacto = cargar_contacto_ponente_desde_mock(telegram_user_id)
    evento = cargar_evento_principal_ponente_desde_mock(telegram_user_id)

    nombre = contacto.get("nombre") or datos.get("nombre_usuario") or "ponente"
    nombre_evento = evento.get("nombre_evento") or "tu evento MITUMI"

    return (
        f"Hola, {nombre}.\n\n"
        f"Soy el asistente de MITUMI para el evento \"{nombre_evento}\".\n\n"
        "Puedes usar los botones para consultas rápidas:\n"
        "✈️ Vuelo · 🏨 Hotel · 🚕 Taxi · 🕒 Horario\n"
        "📍 Lugar · 📄 Documentación · 📞 Contactar MITUMI · 🚨 Urgencia\n\n"
        "También puedes escribir tu pregunta normalmente."
    )


def es_comando_bienvenida(texto: str) -> bool:
    return _normalizar_texto(texto) in COMANDOS_BIENVENIDA


def es_boton_urgencia(texto: str) -> bool:
    texto_norm = _normalizar_texto(texto)
    return "🚨" in texto_norm or texto_norm == _normalizar_texto(BOTON_URGENCIA)


def es_boton_contactar(texto: str) -> bool:
    texto_norm = _normalizar_texto(texto)
    return "📞" in texto_norm or texto_norm == _normalizar_texto(BOTON_CONTACTAR)


def normalizar_payload_boton(payload: dict) -> dict:
    """
    Convierte botones de Telegram en texto explícito para que el agente/LLM los clasifique mejor.
    Mantiene el contrato común intacto.
    """
    datos = payload.get("datos", {}) or {}
    texto = datos.get("texto", "")
    texto_norm = _normalizar_texto(texto)

    if texto_norm in BOTONES_NORMALIZADOS:
        payload = dict(payload)
        payload["datos"] = dict(datos)
        payload["datos"]["texto_original_boton"] = texto
        payload["datos"]["texto"] = BOTONES_NORMALIZADOS[texto_norm]

    return payload


def hay_escalado(resultado: dict) -> bool:
    """Detecta si el resultado del agente debe avisar al admin MITUMI."""
    if resultado.get("requiere_validacion_humana"):
        return True

    datos = resultado.get("datos_detectados", {}) or {}
    if datos.get("urgencia") == "alta":
        return True

    acciones = resultado.get("acciones_propuestas", []) or []
    for accion in acciones:
        if accion.get("tipo") in {"escalar_a_organizacion", "crear_incidencia"}:
            return True

    return False


def construir_mensaje_admin(payload: dict, resultado: dict) -> str:
    """Construye el aviso para el admin cuando el ponente requiere intervención humana."""
    datos_payload = payload.get("datos", {}) or {}
    datos_resultado = resultado.get("datos_detectados", {}) or {}
    acciones = resultado.get("acciones_propuestas", []) or []
    bloqueos = resultado.get("bloqueos_detectados", []) or []

    telegram_user_id = _normalizar_id(datos_payload.get("telegram_user_id"))
    contacto = cargar_contacto_ponente_desde_mock(telegram_user_id)
    evento_mock = cargar_evento_principal_ponente_desde_mock(telegram_user_id)

    nombre = (
        datos_resultado.get("nombre_ponente")
        or contacto.get("nombre")
        or datos_payload.get("nombre_usuario")
        or "No identificado"
    )
    evento = datos_resultado.get("nombre_evento") or evento_mock.get("nombre_evento") or "No disponible"
    telefono = contacto.get("telefono_contacto") or contacto.get("telefono") or "No disponible"
    email = contacto.get("email") or "No disponible"
    mensaje_original = datos_payload.get("texto_original_boton") or datos_payload.get("texto", "")
    intencion = datos_resultado.get("intencion", "No clasificada")
    urgencia = datos_resultado.get("urgencia", "No clasificada")
    resumen = resultado.get("resumen", "Sin resumen")

    motivos = []
    for accion in acciones:
        motivo = accion.get("motivo")
        if motivo:
            motivos.append(str(motivo))
    for bloqueo in bloqueos:
        tipo = bloqueo.get("tipo")
        if tipo:
            motivos.append(str(tipo))

    motivo_texto = ", ".join(motivos) if motivos else "Requiere revisión humana"

    return (
        "🚨 MITUMI - Aviso de ponente\n\n"
        f"Ponente: {nombre}\n"
        f"Evento: {evento}\n"
        f"Teléfono: {telefono}\n"
        f"Email: {email}\n"
        f"Telegram user_id: {telegram_user_id}\n\n"
        f"Urgencia: {urgencia}\n"
        f"Intención: {intencion}\n"
        f"Motivo: {motivo_texto}\n\n"
        f"Mensaje original:\n{mensaje_original}\n\n"
        f"Resumen agente:\n{resumen}"
    )


def construir_resultado_escalado_directo(motivo: str, urgencia: str = "alta") -> dict:
    return {
        "ok": True,
        "resumen": motivo,
        "datos_detectados": {
            "intencion": "incidencia" if urgencia == "alta" else "contactar_mitumi",
            "urgencia": urgencia,
        },
        "acciones_propuestas": [
            {"tipo": "escalar_a_organizacion", "motivo": motivo}
        ],
        "bloqueos_detectados": [],
        "borradores_generados": [],
        "requiere_validacion_humana": True,
        "nivel_riesgo": "medio",
        "errores": [],
    }


def enviar_aviso_admin_si_aplica(payload: dict, resultado: dict) -> None:
    admin_chat_id = obtener_admin_chat_id()

    if not ALLOW_NOTIFY_ADMIN:
        if SHOW_STEPS:
            print("[ADMIN] Aviso admin desactivado por ALLOW_NOTIFY_ADMIN=False")
        return

    if not admin_chat_id:
        if SHOW_STEPS:
            print("[ADMIN] ADMIN_TELEGRAM_CHAT_ID no configurado")
        return

    if not hay_escalado(resultado):
        return

    mensaje_admin = construir_mensaje_admin(payload, resultado)
    respuesta = enviar_mensaje(admin_chat_id, mensaje_admin)

    if SHOW_STEPS:
        print(f"[ADMIN] Aviso enviado al admin: {respuesta.get('ok')}")
        if not respuesta.get("ok"):
            print(f"[ADMIN] Error Telegram: {respuesta}")


def main():
    print("[SERVICIO] agente_telegram_ponentes iniciado")
    print(f"[SERVICIO] Telegram enabled: {TELEGRAM_ENABLED}")
    print(f"[SERVICIO] Envío Telegram permitido: {ALLOW_SEND_TELEGRAM}")
    print(f"[SERVICIO] Admin Telegram configurado: {bool(obtener_admin_chat_id())}")

    ultimo_update_id = None
    ultimo_check_telegram = 0

    while True:
        ahora = time.time()

        if TELEGRAM_ENABLED and ahora - ultimo_check_telegram >= TELEGRAM_CHECK_SECONDS:
            ultimo_check_telegram = ahora

            if SHOW_STEPS:
                print("[TELEGRAM] Buscando mensajes nuevos")

            updates = leer_updates(offset=ultimo_update_id)

            for update in updates:
                ultimo_update_id = update.get("update_id", 0) + 1
                payload = update_a_payload(update)
                if not payload:
                    continue

                datos_payload = payload.get("datos", {}) or {}
                chat_id = datos_payload.get("telegram_chat_id")
                texto_entrada = datos_payload.get("texto", "")
                admin_chat_id = obtener_admin_chat_id()

                # Evita que mensajes escritos por el admin al bot sean tratados como consultas de ponente.
                if admin_chat_id and _normalizar_id(chat_id) == _normalizar_id(admin_chat_id):
                    if es_comando_bienvenida(texto_entrada):
                        enviar_mensaje(chat_id, "Bot MITUMI activo. Este chat está configurado como ADMIN.")
                    elif SHOW_STEPS:
                        print("[TELEGRAM] Mensaje recibido desde admin. Se ignora como consulta de ponente.")
                    continue

                # Bienvenida/menu: no pasa por LLM.
                if es_comando_bienvenida(texto_entrada):
                    texto_bienvenida = construir_mensaje_bienvenida(payload)
                    respuesta = enviar_mensaje_con_botones(chat_id, texto_bienvenida)
                    if SHOW_STEPS:
                        print(f"[PONENTE] Bienvenida enviada con botones: {respuesta.get('ok')}")
                    continue

                # Botón de urgencia: escalado directo al admin.
                if es_boton_urgencia(texto_entrada):
                    texto_ponente = (
                        "🚨 He avisado al equipo de MITUMI.\n\n"
                        "Te contactarán lo antes posible. Si puedes, escribe ahora brevemente qué ocurre."
                    )
                    if chat_id and ALLOW_SEND_TELEGRAM:
                        enviar_mensaje_con_botones(chat_id, texto_ponente)
                    resultado = construir_resultado_escalado_directo("boton_urgencia_pulsado", "alta")
                    enviar_aviso_admin_si_aplica(payload, resultado)
                    continue

                # Botón Contactar MITUMI: escalado no urgente.
                if es_boton_contactar(texto_entrada):
                    texto_ponente = (
                        "📞 He avisado al equipo de MITUMI para que revisen tu consulta.\n\n"
                        "Puedes escribir aquí el motivo para que llegue junto al aviso."
                    )
                    if chat_id and ALLOW_SEND_TELEGRAM:
                        enviar_mensaje_con_botones(chat_id, texto_ponente)
                    resultado = construir_resultado_escalado_directo("solicitud_contacto_mitumi", "normal")
                    enviar_aviso_admin_si_aplica(payload, resultado)
                    continue

                # Botones normales: se normalizan a una consulta explícita para evitar confusiones.
                payload = normalizar_payload_boton(payload)

                resultado = ejecutar_agente(payload)
                texto = extraer_texto_respuesta(resultado)

                # En demo local enviamos también mensajes seguros de escalado al ponente.
                if not texto and hay_escalado(resultado):
                    texto = "He avisado al equipo de MITUMI para que revise tu consulta. Contactarán contigo si es necesario."

                if texto and chat_id and ALLOW_SEND_TELEGRAM:
                    respuesta_ponente = enviar_mensaje_con_botones(chat_id, texto)
                    if SHOW_STEPS:
                        print(f"[PONENTE] Respuesta enviada al ponente: {respuesta_ponente.get('ok')}")
                        if not respuesta_ponente.get("ok"):
                            print(f"[PONENTE] Error Telegram: {respuesta_ponente}")
                elif SHOW_STEPS:
                    print("[SERVICIO] Respuesta no enviada automáticamente")
                    print(resultado.get("resumen"))

                enviar_aviso_admin_si_aplica(payload, resultado)

        time.sleep(SERVICE_LOOP_SECONDS)


if __name__ == "__main__":
    main()
