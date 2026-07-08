"""
Punto de entrada comun de Lumen (Agente 04 - Copilot).

Lo usa main.py (local), y en la arquitectura final el agente orquestador de Agora, ya sea por
import directo o por una futura API. La firma de ejecutar_agente(payload) -> dict es el unico
contrato que NO puede cambiar (ver README.md, seccion 1).

Motor de LLM: Groq (ver src/llm.py). Si no hay API key configurada en .env, o si el LLM falla,
este modulo cae siempre a reglas deterministas - Lumen nunca debe quedarse sin responder.
"""

import json
import re
import unicodedata

from config.permisos import ALLOW_DB_WRITE
from src.schemas import validar_entrada, construir_salida_base
from src.lectura_datos import (
    TablaNoPermitida,
    resumen_evento,
    ponentes_sin_billete_vuelta,
    ponentes_sin_billete_ida,
    contexto_completo_evento,
    estados_disponibles,
    eventos_por_estado,
    todos_los_eventos,
)
from src.validaciones import auditar_salida
from src.prompts import cargar_prompt
from src.llm import llamar_llm, llm_disponible

# Defensa en profundidad: si alguna vez esto no fuera False, preferimos que el agente no arranque
# a que escriba en la BD por error.
assert ALLOW_DB_WRITE is False, "Lumen nunca debe tener ALLOW_DB_WRITE=True."

NOMBRE_AGENTE = "lumen_copilot"

PALABRAS_ESCRITURA = [
    "modifica", "modificar", "actualiza", "actualizar", "borra", "borrar", "elimina", "eliminar",
    "aprueba", "aprobar", "confirma", "confirmar", "sube el presupuesto", "crea un evento",
    "crear evento", "cambia la fecha", "reserva",
]
PALABRAS_USUARIOS = ["usuarios", "contraseña", "contrasenia", "password", "credencial", "credenciales"]

# --- Consultas transversales por estado de evento (sin id_evento) --------------------------
# Nota: los estados reales de este dataset (data/mock/estados.json) son "solicitado",
# "en_preparacion" y "confirmado" - un modelo mas simple que el contrato general de la API
# (que usa borrador/pre-evento/en-curso/finalizado/cancelado). Por eso se mapean sinonimos
# habituales a estos 3 estados reales, y si la frase no encaja con ninguno, Lumen lo dice en
# vez de adivinar (ver _detectar_estado_pedido).
SINONIMOS_ESTADO_EVENTO = {
    "solicitado": ["solicitado", "solicitados", "pendiente", "pendientes", "por confirmar"],
    "en_preparacion": [
        "en preparacion", "preparacion", "en marcha", "en curso", "activo", "activos", "curso",
    ],
    "confirmado": ["confirmado", "confirmados", "confirmada", "confirmadas", "cerrado"],
}

PALABRAS_TRANSVERSAL_ESTADO = [
    "estado", "marcha", "curso", "preparacion", "solicitado", "confirmado",
    "pre-evento", "pre evento", "activos", "pendientes",
]

# Preguntas transversales que NO piden un estado concreto, solo un conteo o listado general
# ("cuantos eventos tenemos", "que eventos hay", "listame los eventos"...).
PALABRAS_TRANSVERSAL_GENERAL = [
    "cuantos", "cuantas", "todos los eventos", "lista de eventos", "listar eventos",
    "listame los eventos", "que eventos hay", "numero de eventos", "total de eventos",
]


def _normalizar(texto):
    """minusculas, sin acentos, sin guiones/underscores -> facilita comparar frases del usuario."""
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.replace("-", " ").replace("_", " ")
    return " ".join(texto.split())


def _parece_consulta_transversal_eventos(pregunta_lower):
    """
    True si la pregunta pinta a una consulta transversal sobre eventos (por estado, o un
    conteo/listado general), sin referirse a un evento concreto por id_evento.
    """
    if "evento" not in pregunta_lower:
        return False
    texto = _normalizar(pregunta_lower)
    todas = PALABRAS_TRANSVERSAL_ESTADO + PALABRAS_TRANSVERSAL_GENERAL
    return any(_normalizar(p) in texto for p in todas)


def _detectar_estado_pedido(pregunta_lower):
    """
    Intenta mapear la frase del usuario a uno de los estados reales de estados.json.
    Devuelve (estado_canonico, True) si hay coincidencia, o (None, False) si no se reconoce
    ningun estado - Lumen no adivina un estado que no existe en los datos.
    """
    texto = _normalizar(pregunta_lower)
    for estado_canonico, sinonimos in SINONIMOS_ESTADO_EVENTO.items():
        for sinonimo in sinonimos:
            if _normalizar(sinonimo) in texto:
                return estado_canonico, True
    return None, False


def ejecutar_agente(payload):
    """
    Punto de entrada comun del agente Lumen.
    Lo usa el main.py local, el orquestador o una futura API.
    """
    errores_entrada = validar_entrada(payload)
    salida = construir_salida_base(NOMBRE_AGENTE, payload.get("tipo_peticion", "desconocido"))

    if errores_entrada:
        salida["ok"] = False
        salida["errores"] = errores_entrada
        salida["resumen"] = "No se pudo procesar la peticion: faltan campos obligatorios."
        return auditar_salida(salida)

    pregunta = (payload.get("datos") or {}).get("pregunta", "")
    pregunta = pregunta.strip()
    pregunta_lower = pregunta.lower()
    id_evento = payload.get("id_evento")
    # Historial opcional de la conversacion (lo rellena la capa de chat, p.ej. chat.py). No es
    # memoria propia de ejecutar_agente -- sigue siendo stateless, el llamador es quien recuerda
    # turnos anteriores y los pasa aqui en cada llamada. Solo se usa para resolver referencias del
    # lenguaje ("ese evento", "su presupuesto") cuando la pregunta pasa por el LLM.
    historial = (payload.get("contexto") or {}).get("historial_conversacion")

    # --- 1. Clasificacion (equivalente a prompts/prompt_clasificar_consulta.md) --------------
    if _contiene_alguna(pregunta_lower, PALABRAS_USUARIOS):
        salida["resumen"] = (
            "Esa consulta esta fuera de mi alcance: no tengo acceso a la tabla 'usuarios' ni a "
            "credenciales de la plataforma."
        )
        salida["bloqueos_detectados"] = ["consulta sobre tabla usuarios / credenciales"]
        salida["nivel_riesgo"] = "alto"
        salida["requiere_validacion_humana"] = True
        return auditar_salida(salida)

    if _contiene_alguna(pregunta_lower, PALABRAS_ESCRITURA):
        salida["resumen"] = (
            "No puedo modificar, aprobar ni borrar datos - solo consulto informacion existente. "
            "Esa accion debe pasar por el orquestador y validacion humana."
        )
        salida["bloqueos_detectados"] = ["la peticion implica una escritura, fuera del alcance de Lumen"]
        salida["nivel_riesgo"] = "medio"
        salida["requiere_validacion_humana"] = True
        return auditar_salida(salida)

    if id_evento is None and _parece_consulta_transversal_eventos(pregunta_lower):
        return _responder_consulta_transversal_eventos(salida, pregunta_lower)

    if id_evento is None and ("billete" in pregunta_lower or "ponente" in pregunta_lower):
        salida["resumen"] = "De que evento (id_evento) necesitas consultar esa informacion?"
        salida["bloqueos_detectados"] = ["falta id_evento para resolver la consulta"]
        return auditar_salida(salida)

    # --- 2. Consulta de solo lectura (equivalente a integrations/api_backend.py) -------------
    try:
        if id_evento is not None and "billete" in pregunta_lower and "vuelta" in pregunta_lower:
            return _responder_ponentes_sin_billete(salida, id_evento, "vuelta")

        if id_evento is not None and "billete" in pregunta_lower and "ida" in pregunta_lower:
            return _responder_ponentes_sin_billete(salida, id_evento, "ida")

        if id_evento is not None:
            # Preguntas libres sobre un evento (presupuesto, sala, espacio, cliente...): si hay
            # LLM configurado, se responde con el prompt de generacion sobre el contexto real
            # del evento. Si el LLM no esta disponible o falla, cae al resumen determinista.
            if llm_disponible():
                resultado_llm = _responder_con_llm(salida, pregunta, id_evento, historial)
                if resultado_llm is not None:
                    return resultado_llm
            return _responder_resumen_evento(salida, id_evento)

    except TablaNoPermitida as exc:
        salida["ok"] = False
        salida["resumen"] = "No puedo acceder a esa informacion: esta fuera de mi alcance de consulta."
        salida["bloqueos_detectados"] = [str(exc)]
        salida["nivel_riesgo"] = "alto"
        salida["requiere_validacion_humana"] = True
        return auditar_salida(salida)

    # --- 3. Sin id_evento y sin patron reconocido en este demo -------------------------------
    salida["resumen"] = (
        "Necesito al menos el id_evento o mas contexto para responder esa pregunta sobre la "
        "plataforma."
    )
    salida["bloqueos_detectados"] = ["consulta sin id_evento y sin patron reconocido en este demo"]
    return auditar_salida(salida)


def _contiene_alguna(texto, palabras):
    """
    Coincidencia por palabra completa (no subcadena). Bug real detectado al probar
    "¿qué eventos están confirmados?": con "in" simple, "confirma" (de PALABRAS_ESCRITURA)
    hacia falso positivo dentro de "confirmados" y bloqueaba una pregunta de solo lectura
    legitima como si fuese una escritura. Con \\b esto ya no ocurre, y "confirma el pedido"
    sigue detectandose igual que antes.
    """
    for palabra in palabras:
        if re.search(r"\b" + re.escape(palabra) + r"\b", texto):
            return True
    return False


def _responder_ponentes_sin_billete(salida, id_evento, tipo):
    obtener = ponentes_sin_billete_vuelta if tipo == "vuelta" else ponentes_sin_billete_ida
    resultado = obtener(id_evento)

    if resultado is None:
        salida["resumen"] = "No encuentro el evento con id_evento " + str(id_evento) + " en los datos disponibles."
        salida["bloqueos_detectados"] = ["id_evento " + str(id_evento) + " no existe en los datos"]
        return auditar_salida(salida)

    nombres = [p["nombre_ponente"] for p in resultado]
    if nombres:
        salida["resumen"] = (
            "El evento " + str(id_evento) + " tiene " + str(len(nombres)) +
            " ponente(s) sin billete de " + tipo + ": " + ", ".join(nombres) + "."
        )
    else:
        salida["resumen"] = (
            "Todos los ponentes del evento " + str(id_evento) +
            " tienen su billete de " + tipo + " registrado."
        )

    salida["datos_detectados"] = {"ponentes_sin_billete_" + tipo: nombres}
    salida["trazas"]["fuentes_consultadas"] = [
        "evento_ponente.billete_" + tipo + "_link",
        "ponentes.nombre_ponente",
    ]
    return auditar_salida(salida)


def _responder_con_llm(salida, pregunta, id_evento, historial=None):
    """
    Responde una pregunta libre sobre un evento usando el LLM (Groq) y el contexto real
    recuperado por src/lectura_datos.py. Devuelve None si el LLM falla o no es utilizable,
    para que el llamador haga fallback a la respuesta determinista.

    `historial` (opcional) es una lista de turnos previos [{"pregunta":..., "resumen":...}, ...]
    que la capa de chat (p.ej. chat.py) mantiene entre llamadas. ejecutar_agente sigue siendo
    stateless: no guarda nada el mismo, solo usa lo que le pasan en este turno para que el LLM
    pueda resolver referencias como "ese evento" o "su presupuesto".

    Nota de seguridad: el LLM solo ve el JSON de contexto_completo_evento(), que ya excluye
    `usuarios` a nivel de codigo. Aunque el LLM alucinase o el usuario intentase manipular el
    prompt, auditar_salida() vuelve a filtrar cualquier mencion a usuarios/contrasenia antes de
    devolver la respuesta.
    """
    contexto = contexto_completo_evento(id_evento)
    if contexto is None:
        salida["resumen"] = "No encuentro el evento con id_evento " + str(id_evento) + " en los datos disponibles."
        salida["bloqueos_detectados"] = ["id_evento " + str(id_evento) + " no existe en los datos"]
        return auditar_salida(salida)

    historial_texto = "(sin historial previo en esta sesion)"
    if historial:
        lineas = []
        for turno in historial[-6:]:
            lineas.append("Usuario: " + str(turno.get("pregunta", "")))
            lineas.append("Lumen: " + str(turno.get("resumen", "")))
        historial_texto = "\n".join(lineas)

    try:
        prompt_sistema = cargar_prompt("prompt_sistema.md")
        prompt_generar = cargar_prompt("prompt_generar_respuesta.md")
        mensaje = (
            prompt_generar + "\n\n"
            "consulta_usuario: " + pregunta + "\n"
            "categoria: consulta_datos_evento\n"
            "datos_recuperados (JSON, la tabla usuarios ya esta excluida de este contexto): " +
            json.dumps(contexto, ensure_ascii=False) + "\n"
            "historial_conversacion (solo para resolver referencias, no es fuente de datos): " +
            historial_texto
        )
        texto = llamar_llm(prompt_sistema, mensaje)
        datos_llm = json.loads(texto)
    except Exception as exc:
        salida.setdefault("errores", []).append("Fallo de LLM, se usa fallback determinista: " + str(exc))
        return None

    salida["resumen"] = datos_llm.get("resumen", "")
    salida["datos_detectados"] = datos_llm.get("datos_detectados", {})
    salida["bloqueos_detectados"] = datos_llm.get("bloqueos_detectados", [])
    if datos_llm.get("requiere_aclaracion"):
        salida["bloqueos_detectados"].append(
            datos_llm.get("pregunta_aclaracion") or "falta informacion para responder"
        )
    salida["trazas"]["fuentes_consultadas"] = datos_llm.get("fuentes", [])
    return auditar_salida(salida)


def _responder_consulta_transversal_eventos(salida, pregunta_lower):
    """
    Responde consultas transversales sin id_evento:
    - '¿qué eventos están en X estado?' -> filtra por ese estado si se reconoce.
    - 'cuántos eventos tenemos / qué eventos hay' -> cuenta/lista todos, sin filtrar.

    'datos_detectados["eventos"]' incluye siempre el id_evento junto al nombre (no solo el
    nombre), para que un llamador con memoria de conversacion (p.ej. chat.py) pueda "engancharse"
    al evento si la respuesta trae uno solo, y luego resolver un "ese evento" en el turno
    siguiente sin tener que volver a pedir el id_evento.
    """
    estado_canonico, coincide = _detectar_estado_pedido(pregunta_lower)

    if coincide:
        eventos = eventos_por_estado(estado_canonico) or []
        estado_legible = estado_canonico.replace("_", " ")
        etiqueta = "en estado '" + estado_legible + "'"
        fuentes = ["eventos.id_estado", "estados.descripcion"]
    else:
        # La pregunta menciona un estado, pero no coincide con ninguno real: no adivinar.
        if _contiene_alguna(pregunta_lower, PALABRAS_TRANSVERSAL_ESTADO):
            disponibles = estados_disponibles()
            salida["resumen"] = (
                "No reconozco ese estado de evento en los datos disponibles. Los estados que "
                "existen son: " + ", ".join(disponibles) + "."
            )
            salida["bloqueos_detectados"] = ["estado de evento no reconocido en la pregunta"]
            salida["datos_detectados"] = {"estados_disponibles": disponibles}
            return auditar_salida(salida)

        eventos = todos_los_eventos()
        etiqueta = "en total"
        fuentes = ["eventos.*"]

    nombres = [e["nombre_evento"] for e in eventos]

    if nombres:
        salida["resumen"] = "Hay " + str(len(nombres)) + " evento(s) " + etiqueta + ": " + ", ".join(nombres) + "."
    else:
        salida["resumen"] = "No hay ningun evento " + etiqueta + " en los datos disponibles."

    salida["datos_detectados"] = {
        "eventos": [{"id_evento": e.get("id_evento"), "nombre_evento": e.get("nombre_evento")} for e in eventos],
    }
    salida["trazas"]["fuentes_consultadas"] = fuentes
    return auditar_salida(salida)


def _responder_resumen_evento(salida, id_evento):
    datos = resumen_evento(id_evento)
    if datos is None:
        salida["resumen"] = "No encuentro el evento con id_evento " + str(id_evento) + " en los datos disponibles."
        salida["bloqueos_detectados"] = ["id_evento " + str(id_evento) + " no existe en los datos"]
        return auditar_salida(salida)

    salida["resumen"] = (
        "Evento " + str(id_evento) + " - " + datos["nombre_evento"] + " (" + datos["ciudad"] + "), " +
        "del " + datos["fecha_inicio"] + " al " + datos["fecha_fin"] + "."
    )
    salida["datos_detectados"] = datos
    salida["trazas"]["fuentes_consultadas"] = ["eventos.*"]
    return auditar_salida(salida)
