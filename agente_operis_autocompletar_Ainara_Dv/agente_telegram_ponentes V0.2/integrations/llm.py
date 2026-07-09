import json

from config.settings import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT_SECONDS,
)

client = None

if LLM_API_KEY:
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        print(f"[LLM] No se pudo crear cliente LLM: {exc}")
        client = None


def extraer_json_desde_texto(contenido: str) -> dict:
    """
    Limpia respuestas del LLM que puedan venir con markdown o texto adicional.
    Devuelve un dict parseado con json.loads().
    """
    if not contenido:
        raise ValueError("Respuesta vacía del LLM")

    texto = contenido.strip()

    texto = texto.replace("```json", "")
    texto = texto.replace("```JSON", "")
    texto = texto.replace("```", "")
    texto = texto.strip()

    inicio = texto.find("{")
    fin = texto.rfind("}")

    if inicio == -1 or fin == -1 or fin <= inicio:
        raise ValueError(f"No se encontró JSON válido en la respuesta del LLM: {contenido}")

    texto_json = texto[inicio:fin + 1]
    return json.loads(texto_json)


def llamar_llm_json(system_prompt: str, user_payload: dict) -> dict:
    """
    Llama al LLM y espera JSON.
    Si no hay API key o falla, usa fallback determinista.
    """
    if client is None:
        return clasificador_simple(user_payload)

    try:
        respuesta = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        )

        contenido = respuesta.choices[0].message.content
        return extraer_json_desde_texto(contenido)

    except Exception as exc:
        print(f"[LLM] Error en llamada LLM: {exc}")
        return clasificador_simple(user_payload)


def clasificador_simple(payload: dict) -> dict:
    """
    Fallback sin LLM para que la demo funcione con reglas básicas.
    Prioriza botones y términos críticos antes que palabras ambiguas.
    """
    texto_original = payload.get("texto") or payload.get("mensaje_ponente") or ""
    texto = texto_original.lower().strip()

    # Botones Telegram: se procesan como mensajes normales.
    if "🚨" in texto or "urgencia" in texto:
        return {
            "intencion": "incidencia",
            "urgencia": "alta",
            "respuesta_ponente": "He avisado al equipo de MITUMI. Te contactarán lo antes posible. Si puedes, escribe ahora brevemente qué ocurre.",
            "requiere_escalado": True,
            "motivo_escalado": "boton_urgencia_o_texto_urgente",
            "confianza": 0.95,
        }

    if "📞" in texto or "contactar mitumi" in texto or "contactar" in texto:
        return {
            "intencion": "contactar_mitumi",
            "urgencia": "normal",
            "respuesta_ponente": "He avisado al equipo de MITUMI para que revisen tu consulta y contacten contigo si es necesario.",
            "requiere_escalado": True,
            "motivo_escalado": "solicitud_contacto_mitumi",
            "confianza": 0.95,
        }

    if "✈" in texto or "vuelo" in texto or "billete" in texto or "avión" in texto or "avion" in texto:
        intencion = "consulta_viaje"
    elif "🚕" in texto or "taxi" in texto or "traslado" in texto or "cómo voy" in texto or "como voy" in texto or "llegar al hotel" in texto or "ir al hotel" in texto:
        intencion = "consulta_taxi"
    elif "🏨" in texto or "hotel" in texto or "duermo" in texto or "alojamiento" in texto or "habitación" in texto or "habitacion" in texto:
        intencion = "consulta_alojamiento"
    elif "📍" in texto or "dónde es" in texto or "donde es" in texto or "lugar" in texto or "ubicación" in texto or "ubicacion" in texto or "dirección" in texto or "direccion" in texto:
        intencion = "consulta_lugar"
    elif "🕒" in texto or "hora" in texto or "horario" in texto or "charla" in texto or "ponencia" in texto or "empieza" in texto:
        intencion = "consulta_horario"
    elif "📄" in texto or "foto" in texto or "cv" in texto or "presentación" in texto or "presentacion" in texto or "ppt" in texto or "documento" in texto:
        intencion = "consulta_documentacion"
    elif any(p in texto for p in ["hola", "buenos días", "buenas", "buenas tardes"]):
        intencion = "saludo"
    else:
        intencion = "otro"

    urgencia = "alta" if any(
        p in texto
        for p in ["urgente", "no encuentro", "sale ya", "sale en", "cancelado", "ya estoy", "perdido", "problema"]
    ) else "normal"

    requiere_escalado = intencion in ["otro"] or urgencia == "alta"

    return {
        "intencion": "incidencia" if urgencia == "alta" else intencion,
        "urgencia": urgencia,
        "respuesta_ponente": "",
        "requiere_escalado": requiere_escalado,
        "motivo_escalado": "fallback_reglas" if requiere_escalado else None,
        "confianza": 0.90 if intencion != "otro" else 0.50,
    }
