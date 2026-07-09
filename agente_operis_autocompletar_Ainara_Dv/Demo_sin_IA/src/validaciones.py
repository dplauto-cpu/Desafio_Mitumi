"""
validaciones.py — validación del contrato de entrada común del proyecto,
adaptado a agente_operis. Ver README.md, sección 9.2, y
Agente_04_Copilot_Raul/lumen_agente_04/src/schemas.py (validar_entrada),
de donde se ha tomado la forma de esta función.
"""

CAMPOS_ENTRADA_OBLIGATORIOS = [
    "tipo_peticion",
    "origen",
    "usuario_solicitante",
    "rol_usuario",
    "datos",
    "contexto",
    "modo",
]


def validar_entrada(payload: dict) -> list:
    """
    Valida el payload de entrada contra el contrato común. Devuelve una
    lista de errores (vacía si el payload es válido).

    Nota sobre id_evento: el contrato común lo describe como "evento
    sobre el que trabaja el agente", pensado para agentes que actúan
    sobre un evento YA existente en la BD. agente_operis es distinto:
    su trabajo es proponer los datos de un evento que todavía no
    existe. Por eso, igual que en Lumen, solo se exige que la clave
    "id_evento" esté presente (para respetar la forma del contrato),
    pero se acepta que su valor sea null.

    Args:
        payload (dict): Payload recibido por ejecutar_agente().

    Returns:
        list: Lista de errores (str). Vacía si el payload es válido.
    """
    errores = []

    if not isinstance(payload, dict):
        return ["El payload debe ser un diccionario JSON."]

    for campo in CAMPOS_ENTRADA_OBLIGATORIOS:
        valor = payload.get(campo, None)
        if campo not in payload or valor in (None, ""):
            errores.append(f"Falta el campo obligatorio '{campo}'.")

    if "id_evento" not in payload:
        errores.append("Falta el campo 'id_evento' (puede ser null: el evento aún no existe en la BD).")

    if not isinstance(payload.get("datos"), dict):
        errores.append("El campo 'datos' debe ser un objeto (dict).")
    elif not payload["datos"].get("texto_briefing"):
        errores.append("payload.datos.texto_briefing es obligatorio (texto del briefing a analizar).")
    else:
        motor = payload["datos"].get("motor", "reglas")
        if motor not in ("reglas", "llm"):
            errores.append(f"payload.datos.motor debe ser 'reglas' o 'llm' (recibido: '{motor}').")

    return errores
