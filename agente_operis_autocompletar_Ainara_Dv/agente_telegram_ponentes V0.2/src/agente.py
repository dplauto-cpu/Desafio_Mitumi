from config.settings import AGENT_NAME
from config.permisos import (
    ESCALATE_UNKNOWN_SPEAKER,
    ESCALATE_MULTIPLE_ACTIVE_EVENTS,
    ESCALATE_MISSING_DATA,
    ESCALATE_LOW_CONFIDENCE,
)
from config.settings import MIN_CONFIDENCE_TO_REPLY, SAVE_CONVERSATION_LOG
from src.funciones import cargar_prompt_compuesto, guardar_log, puede_responder_automaticamente, construir_borrador_telegram
from integrations.llm import llamar_llm_json
from src.schemas import validar_payload_entrada, salida_base, extraer_datos_telegram
from src.herramientas import (
    obtener_ponente_por_telegram,
    obtener_eventos_activos_ponente,
    obtener_info_ponente_evento,
    registrar_comunicacion,
    crear_incidencia,
)
from src.validaciones import validar_decision_llm
from src.rag import consultar_rag


def ejecutar_agente(payload: dict) -> dict:
    """Punto de entrada común del agente.

    Este contrato no debe cambiar: lo usará main.py en local y el orquestador en integración.
    """
    salida = salida_base(payload, ok=True)
    errores_payload = validar_payload_entrada(payload)
    if errores_payload:
        salida["ok"] = False
        salida["resumen"] = "Payload de entrada inválido."
        salida["errores"].extend(errores_payload)
        salida["nivel_riesgo"] = "medio"
        return salida

    datos_telegram = extraer_datos_telegram(payload)
    telegram_user_id = datos_telegram["telegram_user_id"]
    telegram_chat_id = datos_telegram["telegram_chat_id"]
    texto = datos_telegram["texto"]

    if not telegram_user_id or not texto:
        salida["ok"] = False
        salida["resumen"] = "Faltan datos mínimos de Telegram: telegram_user_id o texto."
        salida["errores"].append("faltan_datos_telegram")
        salida["bloqueos_detectados"].append({"tipo": "datos_telegram_incompletos"})
        salida["requiere_validacion_humana"] = True
        return salida

    ponente = obtener_ponente_por_telegram(telegram_user_id)
    salida["trazas"]["fuentes_consultadas"].append("ponente_por_telegram")

    if not ponente:
        texto_respuesta = "No tengo tu usuario vinculado a un ponente registrado. Aviso a la organización para que lo revise."
        salida.update({
            "resumen": "Ponente no identificado por Telegram.",
            "requiere_validacion_humana": True,
            "nivel_riesgo": "medio",
        })
        salida["bloqueos_detectados"].append({"tipo": "ponente_no_identificado", "telegram_user_id": telegram_user_id})
        salida["borradores_generados"].append(construir_borrador_telegram(telegram_chat_id, texto_respuesta, False))
        if ESCALATE_UNKNOWN_SPEAKER:
            salida["acciones_propuestas"].append({"tipo": "escalar_a_organizacion", "motivo": "ponente_no_identificado"})
        crear_incidencia({"tipo": "ponente_no_identificado", "payload": payload})
        _registrar_y_devolver(payload, salida)
        return salida

    id_ponente = ponente.get("id_ponente")
    eventos = obtener_eventos_activos_ponente(id_ponente)
    salida["trazas"]["fuentes_consultadas"].append("eventos_activos_ponente")

    salida["datos_detectados"].update({
        "id_ponente": id_ponente,
        "nombre_ponente": ponente.get("nombre"),
        "telegram_user_id": telegram_user_id,
    })

    if len(eventos) == 0:
        texto_respuesta = "Ahora mismo no encuentro un evento activo asociado a tu perfil. Lo reviso con la organización."
        salida["resumen"] = "El ponente no tiene eventos activos asociados."
        salida["bloqueos_detectados"].append({"tipo": "sin_eventos_activos", "id_ponente": id_ponente})
        salida["borradores_generados"].append(construir_borrador_telegram(telegram_chat_id, texto_respuesta, False))
        salida["requiere_validacion_humana"] = True
        salida["nivel_riesgo"] = "medio"
        if ESCALATE_MISSING_DATA:
            salida["acciones_propuestas"].append({"tipo": "crear_incidencia", "motivo": "sin_eventos_activos"})
        crear_incidencia({"tipo": "sin_eventos_activos", "id_ponente": id_ponente})
        _registrar_y_devolver(payload, salida)
        return salida

    id_evento_payload = payload.get("id_evento") or payload.get("contexto", {}).get("id_evento") or payload.get("datos", {}).get("id_evento")

    if len(eventos) > 1 and not id_evento_payload:
        nombres = ", ".join([e.get("nombre_evento", f"evento {e.get('id_evento')}") for e in eventos])
        texto_respuesta = f"Tienes varios eventos activos: {nombres}. ¿Sobre cuál de ellos me preguntas?"
        salida["resumen"] = "El ponente tiene varios eventos activos y la consulta es ambigua."
        salida["datos_detectados"]["eventos_activos"] = eventos
        salida["bloqueos_detectados"].append({"tipo": "varios_eventos_activos", "eventos": eventos})
        salida["borradores_generados"].append(construir_borrador_telegram(telegram_chat_id, texto_respuesta, True))
        salida["requiere_validacion_humana"] = False
        salida["nivel_riesgo"] = "bajo"
        if ESCALATE_MULTIPLE_ACTIVE_EVENTS:
            salida["acciones_propuestas"].append({"tipo": "solicitar_aclaracion_evento", "canal": "telegram"})
        _registrar_y_devolver(payload, salida)
        return salida

    id_evento = int(id_evento_payload or eventos[0].get("id_evento"))
    info = obtener_info_ponente_evento(id_ponente, id_evento)
    salida["trazas"]["fuentes_consultadas"].append("info_ponente_evento")

    if not info:
        texto_respuesta = "No encuentro tus datos logísticos para este evento. Aviso a la organización para confirmarlo."
        salida["resumen"] = "No se han encontrado datos del ponente para el evento seleccionado."
        salida["datos_detectados"]["id_evento"] = id_evento
        salida["bloqueos_detectados"].append({"tipo": "datos_ponente_evento_no_encontrados", "id_ponente": id_ponente, "id_evento": id_evento})
        salida["borradores_generados"].append(construir_borrador_telegram(telegram_chat_id, texto_respuesta, False))
        salida["requiere_validacion_humana"] = True
        salida["nivel_riesgo"] = "medio"
        crear_incidencia({"tipo": "datos_ponente_evento_no_encontrados", "id_ponente": id_ponente, "id_evento": id_evento})
        _registrar_y_devolver(payload, salida)
        return salida

    contexto_rag = consultar_rag(texto)
    if contexto_rag:
        salida["trazas"]["fuentes_consultadas"].append("rag_local")

    system_prompt = cargar_prompt_compuesto()
    contexto_llm = {
        "mensaje_ponente": texto,
        "ponente": ponente,
        "eventos_activos": eventos,
        "id_evento_seleccionado": id_evento,
        "info_ponente_evento": info,
        "contexto_rag": contexto_rag,
    }
    decision = validar_decision_llm(llamar_llm_json(system_prompt, contexto_llm))

    texto_respuesta = construir_respuesta(decision, info)
    confianza = float(decision.get("confianza", 0.0) or 0.0)
    escalado_por_confianza = confianza < MIN_CONFIDENCE_TO_REPLY and ESCALATE_LOW_CONFIDENCE
    requiere_escalado = bool(decision.get("requiere_escalado")) or escalado_por_confianza

    if escalado_por_confianza:
        texto_respuesta = "He recibido tu consulta. Prefiero confirmarlo con la organización antes de darte un dato incorrecto."

    apto_envio = not requiere_escalado and puede_responder_automaticamente()

    salida["resumen"] = f"Consulta de ponente clasificada como {decision.get('intencion')}."
    salida["datos_detectados"].update({
        "id_evento": id_evento,
        "nombre_evento": info.get("nombre_evento"),
        "intencion": decision.get("intencion"),
        "urgencia": decision.get("urgencia"),
        "confianza": confianza,
        "respuesta_ponente": texto_respuesta,
    })
    salida["borradores_generados"].append(construir_borrador_telegram(telegram_chat_id, texto_respuesta, apto_envio))
    salida["requiere_validacion_humana"] = requiere_escalado
    salida["nivel_riesgo"] = "medio" if requiere_escalado else "bajo"

    if requiere_escalado:
        salida["acciones_propuestas"].append({
            "tipo": "escalar_a_organizacion",
            "motivo": decision.get("motivo_escalado") or "confianza_baja_o_dato_sensible",
        })
    else:
        salida["acciones_propuestas"].append({
            "tipo": "responder_telegram",
            "canal": "telegram",
            "requiere_permiso_envio": True,
        })

    if not puede_responder_automaticamente():
        salida["bloqueos_detectados"].append({"tipo": "fuera_de_horario_ordinario"})

    registrar_comunicacion({
        "agente": AGENT_NAME,
        "telegram_user_id": telegram_user_id,
        "id_ponente": id_ponente,
        "id_evento": id_evento,
        "texto_entrada": texto,
        "salida": salida,
    })
    _registrar_y_devolver(payload, salida)
    return salida


def construir_respuesta(decision: dict, info: dict) -> str:
    intencion = decision.get("intencion")

    if intencion == "consulta_alojamiento":
        hotel = info.get("hotel")
        direccion_hotel = info.get("direccion_hotel")
        if hotel and direccion_hotel:
            return f"🏨 Tu alojamiento es: {str(hotel).rstrip('.')}. Dirección: {direccion_hotel}."
        if hotel:
            return f"🏨 Tu alojamiento es: {str(hotel).rstrip('.')}."
        return "No tengo confirmado el hotel en los datos del evento. Lo consulto con la organización."

    if intencion == "consulta_viaje":
        vuelo = info.get("vuelo")
        viaje = info.get("viaje")
        if vuelo:
            return f"✈️ Estos son los datos de vuelo/viaje que tengo registrados: {str(vuelo).rstrip('.')}."
        if viaje:
            return f"✈️ Estos son los datos de viaje que tengo registrados: {str(viaje).rstrip('.')}."
        return "No tengo datos de viaje confirmados. Lo reviso con la organización."

    if intencion == "consulta_taxi":
        taxi_llegada = info.get("taxi_llegada")
        taxi_salida = info.get("taxi_salida")
        taxi = info.get("taxi")
        if taxi_llegada or taxi_salida:
            partes = []
            if taxi_llegada:
                partes.append(f"Llegada: {taxi_llegada}")
            if taxi_salida:
                partes.append(f"Salida: {taxi_salida}")
            return "🚕 Traslados previstos: " + " | ".join(partes) + "."
        if taxi:
            return f"🚕 Traslado previsto: {str(taxi).rstrip('.')}."
        viaje = info.get("viaje")
        if viaje and "taxi" in str(viaje).lower():
            return f"🚕 En tus datos de viaje consta: {str(viaje).rstrip('.')}."
        return "No tengo un taxi confirmado en los datos del evento. Lo reviso con la organización."

    if intencion == "consulta_horario":
        horario = info.get("horario_ponencia")
        if horario:
            return f"🕒 Tu ponencia está prevista a las {horario}."
        return "No tengo el horario confirmado. Lo reviso con la organización."

    if intencion == "consulta_lugar":
        lugar = info.get("lugar")
        sala = info.get("sala")
        if lugar and sala:
            return f"📍 Tu ponencia será en {lugar}. Sala: {sala}."
        if lugar:
            return f"📍 Tu ponencia será en {lugar}."
        return "No tengo confirmado el lugar de la ponencia. Lo reviso con la organización."

    if intencion == "consulta_documentacion":
        pendientes = info.get("documentos_pendientes", [])
        if pendientes:
            return "📄 Tienes pendiente enviar: " + ", ".join(pendientes) + "."
        return "📄 No veo documentación pendiente en este momento."

    if intencion == "contactar_mitumi":
        return "He avisado al equipo de MITUMI para que revisen tu consulta."

    if intencion == "incidencia":
        respuesta = decision.get("respuesta_ponente")
        if respuesta:
            return respuesta
        return "He avisado al equipo de MITUMI. Te contactarán lo antes posible."

    if intencion == "saludo":
        return "Hola. Puedes usar los botones del menú para consultar viaje, hotel, taxi, horario, lugar, documentación o urgencias."

    respuesta = decision.get("respuesta_ponente")
    if respuesta:
        return respuesta

    return "He recibido tu mensaje. Si necesitas confirmar algún dato concreto, lo reviso con la organización."

def _registrar_y_devolver(payload: dict, salida: dict) -> None:
    if SAVE_CONVERSATION_LOG:
        guardar_log("conversaciones.jsonl", {"payload": payload, "salida": salida})
