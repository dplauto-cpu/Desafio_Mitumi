"""
nucleo.py — lógica real de ejecutar_agente(payload). src/agente.py solo
reexporta esta función: es el punto de entrada estable que el
orquestador, main.py o una futura API deben poder importar siempre
igual, mientras la implementación puede evolucionar aquí (mismo patrón
que Agente_04_Copilot_Raul/lumen_agente_04/src/agente.py + src/nucleo.py).
"""

import datetime

from config import settings
from src.schemas import construir_salida_base
from src.validaciones import validar_entrada
from src import funciones


def ejecutar_agente(payload: dict) -> dict:
    """
    Punto de entrada común del agente. Lo usa main.py (uso local), el
    orquestador, o una futura API.

    Args:
        payload (dict): Contrato de entrada común — ver
            src/validaciones.py y README.md, sección 9.2. Debe incluir
            payload["datos"]["texto_briefing"] con el texto ya extraído
            del documento (la ingesta de .pdf/.docx/.txt la hace
            funciones.leer_archivo() antes de construir el payload —
            ver main.py para un ejemplo).

    Returns:
        dict: Contrato de salida común — ver src/schemas.py y
            README.md, sección 9.3. datos_detectados siempre trae los
            6 bloques (evento, cliente, espacio, sala, presupuesto,
            ponentes); requiere_validacion_humana es SIEMPRE True — es
            la regla de oro de este agente (ver
            Documentacion_agentes/Agente_OPERIS.md).
    """
    tipo_peticion = payload.get("tipo_peticion", "extraer_briefing") if isinstance(payload, dict) else "extraer_briefing"
    salida = construir_salida_base(tipo_peticion)

    errores = validar_entrada(payload)
    if errores:
        salida["ok"] = False
        salida["resumen"] = "; ".join(errores)
        salida["errores"] = errores
        salida["nivel_riesgo"] = "bajo"
        return salida

    datos = payload.get("datos", {})
    texto = datos.get("texto_briefing", "")
    motor = datos.get("motor", settings.MOTOR_POR_DEFECTO)

    try:
        if motor == "llm":
            # Import perezoso: así el motor de reglas (el caso más
            # habitual) no necesita tener el paquete `groq` instalado.
            from src.llm import extraer_briefing_llm
            resultado = extraer_briefing_llm(texto)
            fuente = f"llm:{settings.GROQ_MODEL}"
        else:
            resultado = funciones.extraer_briefing(texto)
            fuente = "motor:reglas"
    except Exception as e:
        salida["ok"] = False
        salida["resumen"] = f"Error al extraer el briefing con el motor '{motor}': {e}"
        salida["errores"] = [str(e)]
        return salida

    datos_detectados = {
        clave: valor for clave, valor in resultado.items() if not clave.startswith("_")
    }

    salida["resumen"] = resultado["_aviso_agente"]["mensaje"]
    salida["datos_detectados"] = datos_detectados
    salida["bloqueos_detectados"] = resultado["_validacion"]["campos_pendientes"]
    salida["requiere_validacion_humana"] = True
    salida["trazas"]["fuentes_consultadas"] = [fuente]
    salida["trazas"]["timestamp"] = datetime.datetime.now().isoformat(timespec="seconds")

    return salida
