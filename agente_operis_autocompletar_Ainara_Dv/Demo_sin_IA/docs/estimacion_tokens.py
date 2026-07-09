# estimacion_tokens.py
# =====================================================================
# ESTIMACIÓN DE USO DE TOKENS DEL MOTOR LLM (src/llm.py)
# =====================================================================
# Calcula una estimación de tokens/coste para el motor LLM de Operis
# (Groq, openai/gpt-oss-120b) en dos casos: un briefing simple
# (data/ejemplos/briefing_prueba.txt) y uno complejo con varios espacios
# candidatos, servicios y ponentes (data/ejemplos/briefing_complejo.txt).
#
# Ejecutar con: python docs/estimacion_tokens.py (desde la raíz del
# agente, agente_operis/). Genera (o regenera) docs/ESTIMACION_TOKENS.md
# con el informe.
#
# METODOLOGÍA (leer antes de confiar en los números):
#   - El prompt de sistema y el texto de entrada del usuario se miden
#     de forma exacta y reproducible con tiktoken (son texto real,
#     determinista).
#   - openai/gpt-oss-120b usa el formato "harmony" de OpenAI, cuyo
#     tokenizador exacto no está disponible como paquete instalable.
#     Se usa la codificación pública o200k_base (misma familia OpenAI,
#     la más cercana disponible) como aproximación — los números son
#     una ESTIMACIÓN, no una medición exacta de la API real.
#   - La salida (el JSON que devolvería el LLM) no se puede medir sin
#     hacer una llamada real. Se estima con un JSON de ejemplo
#     razonable para cada caso: para el caso simple, se reutiliza la
#     salida real del motor de reglas (funciones.extraer_briefing), que
#     para ese texto consigue el 100% de los campos obligatorios; para
#     el caso complejo, se ha construido a mano la salida que debería
#     producir una extracción correcta (el motor de reglas sí detecta
#     los 4 ponentes del bloque "Ponente N" de este ejemplo, con sus
#     campos etiquetados de forma limpia -- nombre, DNI, email,
#     teléfono, empresa, cargo, sector, hotel -- pero no interpreta
#     prosa libre mezclada en la misma línea, como el horario o el
#     tipo de cada ponencia, así que no sirve de referencia para ESOS
#     campos en concreto; sí lo sería, en cambio, si solo se pidiera
#     estimar el motor de reglas).
#   - Precios de openai/gpt-oss-120b en Groq (verificados en julio de
#     2026): $0.15 / 1M tokens de entrada, $0.60 / 1M tokens de salida.
#   - Free tier de Groq para este modelo (verificado en julio de 2026):
#     1000 peticiones/día, 200.000 tokens/día.
# =====================================================================

import sys
import json
from pathlib import Path

import tiktoken

BASE_DIR = Path(__file__).resolve().parent.parent  # agente_operis/
sys.path.insert(0, str(BASE_DIR))

from src.llm import construir_prompt_sistema  # noqa: E402
from config import settings as parametros  # noqa: E402
from src.funciones import leer_archivo, extraer_briefing  # noqa: E402

ENCODING = "o200k_base"
PRECIO_INPUT_POR_M = 0.15
PRECIO_OUTPUT_POR_M = 0.60
LIMITE_TPD_FREE = 200_000
LIMITE_RPD_FREE = 1000

_enc = tiktoken.get_encoding(ENCODING)


def contar_tokens(texto):
    return len(_enc.encode(texto))


def _quitar_metadatos(resultado):
    """
    El LLM solo devuelve los 6 bloques de datos (evento/cliente/espacio/
    sala/presupuesto/ponentes) — _aviso_agente y _validacion los añade
    generar_aviso_y_validacion() DESPUÉS, en local. Para estimar el
    tamaño real de la respuesta del LLM hay que excluirlos.
    """
    return {
        clave: valor
        for clave, valor in resultado.items()
        if not clave.startswith("_")
    }


# ---------------------------------------------------------------------
# Salida esperada para el caso complejo (construida a mano — ver nota
# de metodología arriba). Representa lo que debería devolver una
# extracción correcta de briefing_complejo.txt.
# ---------------------------------------------------------------------
SALIDA_ESPERADA_COMPLEJA = {
    "evento": {
        "nombre_evento": "III Congreso Internacional de Movilidad Sostenible",
        "ciudad": "Bilbao",
        "lugar_confirmado": "",
        "fecha_inicio": "12/11/2026",
        "fecha_fin": "14/11/2026",
        "numero_personas": "850",
        "tipo_evento": "Congreso",
        "estado": "",
        "nota": "Formato congreso + zona de exposición de vehículos eléctricos. Taller paralelo de movilidad eléctrica urbana, día 13 por la mañana, aforo 60 personas."
    },
    "cliente": {
        "cliente": "Marta Ruiz",
        "empresa": "Iberdrola Innovación S.L.",
        "email": "marta.ruiz@iberdrola-innovacion.es",
        "telefono": "944 002 222",
        "sector": "",
        "ciudad": "Bilbao"
    },
    "espacio": {
        "nombre_espacio": "BEC (Bilbao Exhibition Centre)",
        "ciudad": "Barakaldo",
        "direccion": "",
        "capacidad_total": "5000",
        "aforo": "",
        "nota": "Opción principal (Pabellón 1 y 2 para exposición + auditorio para ponencias). Alternativas en comparación: Palacio Euskalduna (Bilbao, auditorio 2000 personas) y Artium Museoa (Vitoria-Gasteiz, solo día 14, 300 personas).",
        "telefono_contacto": "",
        "nombre_contacto": "",
        "email_contacto": ""
    },
    "sala": {
        "nombre_sala": "Auditorio principal",
        "tipo": "Auditorio",
        "capacidad_max_sala": "850",
        "nota_sala": "Sala adicional para taller práctico, aforo 60 personas, día 13 por la mañana."
    },
    "presupuesto": {
        # "Pendiente" — valor real de presupuestos.csv (ver status_3.py:
        # BUDGET_STATUS ya no incluye "Pendiente de aprobación", que no
        # existía en los datos reales de la BD).
        "estado_presupuesto": "Pendiente",
        "total": "180000",
        "fecha": "",
        "nota_ubicacion": "",
        "precio_ubicacion": "",
        "precio_catering": "",
        "precio_audiovisuales": "",
        "precio_otros": "",
        "nota_catering": "",
        "nota_audiovisuales": "",
        "nota_otros": "",
        "observaciones": "Servicios solicitados: catering (3 jornadas), audiovisuales completos (streaming, traducción simultánea inglés-español, sonido e iluminación), seguridad privada, parking para 200 vehículos, wifi de alta capacidad."
    },
    "ponentes": [
        {
            "nombre_ponente": "Elena Gómez", "doc_identificacion": "15003333Z",
            "email": "elena.gomez@bbva.com", "sector": "Banca",
            "telefono": "915 003 333", "foto_link": "", "cv_link": "",
            "empresa": "BBVA", "cargo": "Directora de Sostenibilidad",
            "nombre_hotel": "NH Collection Bilbao",
            "nota_transporte": "Traslado desde el aeropuerto día 11 por la tarde, vuelta día 12 por la noche.",
            "horario_ida_transporte": "", "horario_vuelta_transporte": "",
            "localizacion_hotel": "", "horario_ponencia": "2026-11-12 09:30",
            "checking_horario": "", "ponente_estado": "Confirmado",
            "presentacion_link": "", "billete_ida_link": "", "billete_vuelta_link": "",
            "tipo_ponencias": "Keynote de apertura"
        },
        {
            "nombre_ponente": "Jordi Valls", "doc_identificacion": "32004444B",
            "email": "jvalls@seat.es", "sector": "Automoción",
            "telefono": "932 004 444", "foto_link": "", "cv_link": "",
            "empresa": "SEAT", "cargo": "Responsable de Movilidad Eléctrica",
            "nombre_hotel": "",
            "nota_transporte": "Requiere alojamiento la noche del día 12.",
            "horario_ida_transporte": "", "horario_vuelta_transporte": "",
            "localizacion_hotel": "", "horario_ponencia": "2026-11-13 11:00",
            "checking_horario": "", "ponente_estado": "Confirmado",
            "presentacion_link": "", "billete_ida_link": "", "billete_vuelta_link": "",
            "tipo_ponencias": "Mesa redonda: el futuro del vehículo eléctrico"
        },
        {
            "nombre_ponente": "Ane Etxeberria", "doc_identificacion": "",
            "email": "", "sector": "I+D",
            "telefono": "", "foto_link": "", "cv_link": "",
            "empresa": "Tecnalia", "cargo": "Investigadora principal, área de energía",
            "nombre_hotel": "", "nota_transporte": "No ha confirmado alojamiento ni transporte.",
            "horario_ida_transporte": "", "horario_vuelta_transporte": "",
            "localizacion_hotel": "", "horario_ponencia": "2026-11-13 16:30",
            "checking_horario": "", "ponente_estado": "Pendiente",
            "presentacion_link": "", "billete_ida_link": "", "billete_vuelta_link": "",
            "tipo_ponencias": "Charla técnica: baterías de nueva generación"
        },
        {
            "nombre_ponente": "Carlos Barrabés", "doc_identificacion": "",
            "email": "c.barrabes@innovacion.es", "sector": "Tecnología",
            "telefono": "600 111 222", "foto_link": "", "cv_link": "",
            "empresa": "Barrabés", "cargo": "CEO",
            "nombre_hotel": "", "nota_transporte": "",
            "horario_ida_transporte": "", "horario_vuelta_transporte": "",
            "localizacion_hotel": "", "horario_ponencia": "2026-11-14 12:00",
            "checking_horario": "", "ponente_estado": "Confirmado",
            "presentacion_link": "", "billete_ida_link": "", "billete_vuelta_link": "",
            "tipo_ponencias": "Clausura (conversación con el público)"
        }
    ]
}


def analizar_caso(nombre_caso, ruta_archivo, salida_esperada):
    texto = leer_archivo(str(ruta_archivo))

    prompt_sistema = construir_prompt_sistema()
    tokens_sistema = contar_tokens(prompt_sistema)
    tokens_entrada_usuario = contar_tokens(texto)
    tokens_input_total = tokens_sistema + tokens_entrada_usuario

    salida_json = json.dumps(salida_esperada, ensure_ascii=False)
    tokens_salida = contar_tokens(salida_json)

    coste_input = tokens_input_total / 1_000_000 * PRECIO_INPUT_POR_M
    coste_output = tokens_salida / 1_000_000 * PRECIO_OUTPUT_POR_M
    coste_total = coste_input + coste_output
    tokens_totales = tokens_input_total + tokens_salida

    llamadas_por_dia_tpd = LIMITE_TPD_FREE // tokens_totales if tokens_totales else 0
    llamadas_por_dia_free = min(llamadas_por_dia_tpd, LIMITE_RPD_FREE)

    return {
        "caso": nombre_caso,
        "archivo": str(ruta_archivo),
        "caracteres_texto": len(texto),
        "tokens_sistema": tokens_sistema,
        "tokens_entrada_usuario": tokens_entrada_usuario,
        "tokens_input_total": tokens_input_total,
        "tokens_salida_estimados": tokens_salida,
        "tokens_totales": tokens_totales,
        "coste_input_usd": coste_input,
        "coste_output_usd": coste_output,
        "coste_total_usd": coste_total,
        "llamadas_por_dia_en_free_tier": llamadas_por_dia_free,
        "cuello_de_botella_free_tier": "tokens/día" if llamadas_por_dia_tpd < LIMITE_RPD_FREE else "peticiones/día",
    }


def formatear_informe(casos):
    lineas = []
    lineas.append("# Estimación de uso de tokens — motor LLM de Operis")
    lineas.append("")
    lineas.append(
        "Generado automáticamente por `docs/estimacion_tokens.py`. Modelo: "
        f"`{parametros.GROQ_MODEL}` en Groq. "
        f"Codificación usada para estimar tokens: `{ENCODING}` "
        "(aproximación — ver metodología en la cabecera de `estimacion_tokens.py`)."
    )
    lineas.append("")
    lineas.append(
        f"Precios: ${PRECIO_INPUT_POR_M}/1M tokens entrada, "
        f"${PRECIO_OUTPUT_POR_M}/1M tokens salida. "
        f"Free tier: {LIMITE_RPD_FREE} peticiones/día, {LIMITE_TPD_FREE:,} tokens/día."
    )
    lineas.append("")
    lineas.append("## Resumen comparativo")
    lineas.append("")
    lineas.append("| | " + " | ".join(c["caso"] for c in casos) + " |")
    lineas.append("|---|" + "---|" * len(casos))

    filas = [
        ("Caracteres del briefing", "caracteres_texto", "{:,}"),
        ("Tokens del prompt de sistema (fijo)", "tokens_sistema", "{:,}"),
        ("Tokens del texto del briefing", "tokens_entrada_usuario", "{:,}"),
        ("Tokens de entrada totales", "tokens_input_total", "{:,}"),
        ("Tokens de salida (JSON estimado)", "tokens_salida_estimados", "{:,}"),
        ("Tokens totales por llamada", "tokens_totales", "{:,}"),
        ("Coste entrada (USD)", "coste_input_usd", "${:.6f}"),
        ("Coste salida (USD)", "coste_output_usd", "${:.6f}"),
        ("Coste total por llamada (USD)", "coste_total_usd", "${:.6f}"),
        ("Llamadas/día posibles en free tier", "llamadas_por_dia_en_free_tier", "{:,}"),
        ("Límite que se agota primero", "cuello_de_botella_free_tier", "{}"),
    ]

    for etiqueta, clave, formato in filas:
        valores = [formato.format(c[clave]) for c in casos]
        lineas.append(f"| {etiqueta} | " + " | ".join(valores) + " |")

    lineas.append("")
    lineas.append("## Lectura de los resultados")
    lineas.append("")
    lineas.append(
        "- El **prompt de sistema pesa lo mismo en los dos casos** (es fijo, "
        "define el esquema) y es la parte dominante del coste de entrada en "
        "el caso simple — normal en una tarea de extracción de un solo "
        "documento corto: el \"overhead\" fijo del esquema pesa más que el "
        "propio texto."
    )
    lineas.append(
        "- En el caso complejo, el texto de entrada y sobre todo la salida "
        "(4 ponentes con toda su ficha de logística) crecen mucho más que "
        "proporcionalmente al número de líneas del briefing — la lista de "
        "ponentes es la parte más cara de la respuesta."
    )
    lineas.append(
        "- **Limitación de esquema detectada al construir el caso complejo:** "
        "el bloque `espacio` es un único objeto, no una lista — no modela bien "
        "un briefing que compara varios espacios candidatos a la vez (aquí, "
        "BEC / Palacio Euskalduna / Artium Museoa). En la estimación, el "
        "espacio principal se guarda en `espacio` y las alternativas quedan "
        "resumidas como texto en `espacio.nota`. Si este caso de uso "
        "(comparar espacios) es habitual, `espacio` debería pasar a ser una "
        "lista, igual que `ponentes` — no se ha tocado el esquema ahora para "
        "no romper la compatibilidad con las apps ya hechas, pero queda "
        "anotado para una futura iteración."
    )
    lineas.append(
        "- En los dos casos, el límite que se agota primero en el free tier "
        "es el de **tokens/día** (200.000), no el de peticiones/día (1000): "
        "con briefings de este tamaño se llega a 66–147 llamadas/día antes de "
        "agotar tokens, muy por debajo del límite de peticiones. Es decir, "
        "para este agente el free tier de Groq rinde menos peticiones de las "
        "1000 nominales — al contrario que en Vigil, cuyas convocatorias de "
        "licitación son más cortas y sí llegarían a agotar antes las "
        "peticiones/día que los tokens/día."
    )
    lineas.append("")

    return "\n".join(lineas)


def main():
    ejemplos_dir = BASE_DIR / "data" / "ejemplos"

    caso_simple = analizar_caso(
        "Simple (briefing_prueba.txt)",
        ejemplos_dir / "briefing_prueba.txt",
        _quitar_metadatos(extraer_briefing(leer_archivo(str(ejemplos_dir / "briefing_prueba.txt")))),
    )
    caso_complejo = analizar_caso(
        "Complejo (briefing_complejo.txt)",
        ejemplos_dir / "briefing_complejo.txt",
        SALIDA_ESPERADA_COMPLEJA,
    )

    casos = [caso_simple, caso_complejo]

    informe = formatear_informe(casos)

    ruta_informe = Path(__file__).resolve().parent / "ESTIMACION_TOKENS.md"
    with open(ruta_informe, "w", encoding="utf-8") as f:
        f.write(informe)

    print(informe)
    print(f"\n(Informe guardado también en {ruta_informe})")


if __name__ == "__main__":
    main()
