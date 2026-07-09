"""
llm.py — motor de extracción alternativo al de reglas/regex de
funciones.py. Usa un LLM en Groq (por defecto openai/gpt-oss-120b —
ver config/settings.py) para rellenar el MISMO esquema de salida que
funciones.extraer_briefing(), a partir del texto libre del briefing.

El prompt de sistema vive en prompts/prompt_sistema.md (no embebido
aquí) — mismo patrón que
Agente_04_Copilot_Raul/lumen_agente_04/src/llm.py + prompts/*.md.

Regla de oro: el LLM nunca debe inventar un dato. Si un campo no
aparece explícitamente en el texto, su valor debe ser "" (cadena
vacía) o [] (listas), nunca una suposición. Por eso: temperature=0,
response_format json_object, y un prompt que lo exige explícitamente.
"""

import json
from pathlib import Path

from config import settings
from src.schemas import crear_estructura_vacia_completa, generar_aviso_y_validacion

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_PROMPT_SISTEMA = BASE_DIR / "prompts" / "prompt_sistema.md"

# Mismas claves, en el mismo orden de bloques, que
# schemas.crear_estructura_vacia_completa() — si ese esquema cambia,
# hay que actualizar este también.
ESQUEMA_SALIDA = {
    "evento": [
        "nombre_evento", "ciudad", "lugar_confirmado", "fecha_inicio",
        "fecha_fin", "numero_personas", "tipo_evento", "estado", "nota"
    ],
    "cliente": ["cliente", "empresa", "email", "telefono", "sector", "ciudad"],
    "espacio": [
        "nombre_espacio", "ciudad", "direccion", "capacidad_total", "aforo",
        "nota", "telefono_contacto", "nombre_contacto", "email_contacto"
    ],
    "sala": ["nombre_sala", "tipo", "capacidad_max_sala", "nota_sala"],
    "presupuesto": [
        "estado_presupuesto", "total", "fecha", "nota_ubicacion",
        "precio_ubicacion", "precio_catering", "precio_audiovisuales",
        "precio_otros", "nota_catering", "nota_audiovisuales", "nota_otros",
        "observaciones"
    ],
    "ponentes": [
        "nombre_ponente", "doc_identificacion", "email", "sector", "telefono",
        "foto_link", "cv_link", "empresa", "cargo", "nombre_hotel",
        "nota_transporte", "horario_ida_transporte", "horario_vuelta_transporte",
        "localizacion_hotel", "horario_ponencia", "checking_horario",
        "ponente_estado", "presentacion_link", "billete_ida_link",
        "billete_vuelta_link", "tipo_ponencias"
    ]
}


def construir_prompt_sistema():
    """Carga prompts/prompt_sistema.md y le inserta el esquema de salida."""
    plantilla = RUTA_PROMPT_SISTEMA.read_text(encoding="utf-8")
    return plantilla.format(
        esquema=json.dumps(ESQUEMA_SALIDA, ensure_ascii=False, indent=2)
    )


def _fusionar_sobre_plantilla(datos_llm):
    """
    Fusiona lo que devuelve el LLM sobre la plantilla vacía completa, para
    que un bloque o campo que el LLM haya omitido (pese a la instrucción)
    no rompa el resto del pipeline — se queda simplemente en "".

    Args:
        datos_llm (dict): JSON ya parseado que devolvió el LLM.

    Returns:
        dict: Estructura completa (mismo esquema que el motor de reglas).
    """
    resultado = crear_estructura_vacia_completa()

    for bloque in ("evento", "cliente", "espacio", "sala", "presupuesto"):
        valores_llm = datos_llm.get(bloque)
        if isinstance(valores_llm, dict):
            for campo in resultado[bloque]:
                if campo in valores_llm and valores_llm[campo] is not None:
                    resultado[bloque][campo] = str(valores_llm[campo]).strip()

    ponentes_llm = datos_llm.get("ponentes")
    if isinstance(ponentes_llm, list):
        claves_ponente = ESQUEMA_SALIDA["ponentes"]
        ponentes = []
        for ponente_llm in ponentes_llm:
            if not isinstance(ponente_llm, dict):
                continue
            ponente = {clave: "" for clave in claves_ponente}
            for clave in claves_ponente:
                if clave in ponente_llm and ponente_llm[clave] is not None:
                    ponente[clave] = str(ponente_llm[clave]).strip()
            ponentes.append(ponente)
        resultado["ponentes"] = ponentes

    return resultado


def extraer_briefing_llm(texto, api_key=None, model=None):
    """
    Extrae la información del briefing usando un LLM en Groq, en vez de
    los heurísticos de texto libre de funciones.py. Mismo esquema de
    salida que funciones.extraer_briefing() — ambos motores son
    intercambiables.

    Requiere:
        - El paquete `groq` instalado (pip install groq).
        - GROQ_API_KEY configurada (.env o variable de entorno).

    Args:
        texto (str): Texto completo del briefing.
        api_key (str): Clave de API de Groq. Si no se indica, se usa
            config.settings.GROQ_API_KEY.
        model (str): Modelo de Groq a usar. Por defecto,
            config.settings.GROQ_MODEL ("openai/gpt-oss-120b").

    Returns:
        dict: Mismo esquema que funciones.extraer_briefing() (evento,
            cliente, espacio, sala, presupuesto, ponentes,
            _aviso_agente, _validacion).

    Raises:
        ImportError: si el paquete `groq` no está instalado.
        ValueError: si falta GROQ_API_KEY, o si el LLM devuelve un JSON
            inválido (nunca se intenta "adivinar" un JSON mal formado).
    """
    try:
        from groq import Groq
    except ImportError:
        raise ImportError(
            "El motor LLM requiere el paquete 'groq'. Instálalo con: "
            "pip install groq"
        )

    api_key = api_key or settings.GROQ_API_KEY
    if not api_key:
        raise ValueError(
            "Falta GROQ_API_KEY. Defínela en .env (o pásala como argumento) "
            "antes de usar el motor LLM. El motor de reglas "
            "(src.funciones.extraer_briefing) sigue disponible sin clave."
        )

    cliente_groq = Groq(api_key=api_key)

    respuesta = cliente_groq.chat.completions.create(
        model=model or settings.GROQ_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": construir_prompt_sistema()},
            {"role": "user", "content": texto},
        ],
    )

    contenido = respuesta.choices[0].message.content

    try:
        datos_llm = json.loads(contenido)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"El LLM devolvió un JSON inválido: {e}\nContenido recibido: {contenido}"
        )

    resultado = _fusionar_sobre_plantilla(datos_llm)
    return generar_aviso_y_validacion(resultado)
