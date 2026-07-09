"""
schemas.py — esquema de los datos propuestos por agente_operis + base
del contrato de salida común del proyecto (ver README.md, secciones 9 y
10; y Agente_04_Copilot_Raul/lumen_agente_04/src/schemas.py, del que
se ha tomado la forma de construir_salida_base).
"""

import datetime
import re

NOMBRE_AGENTE = "agente_operis"


# ---------------------------------------------------------------------
# 1. BASE DEL CONTRATO DE SALIDA (contrato común del proyecto)
# ---------------------------------------------------------------------
def construir_salida_base(tipo_peticion: str) -> dict:
    """Construye la salida base con el contrato común, lista para rellenar."""
    return {
        "ok": True,
        "agente": NOMBRE_AGENTE,
        "tipo_peticion": tipo_peticion,
        "resumen": "",
        "datos_detectados": {},
        "acciones_propuestas": [],
        "bloqueos_detectados": [],
        "borradores_generados": [],
        "requiere_validacion_humana": True,  # siempre True en agente_operis — regla de oro
        "nivel_riesgo": "bajo",  # agente_operis nunca escribe ni envía nada: riesgo siempre bajo
        "errores": [],
        "trazas": {
            "fuentes_consultadas": [],
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "modo": "propuesta",
        },
    }


# ---------------------------------------------------------------------
# 2. ESQUEMA DE LOS DATOS PROPUESTOS (dentro de datos_detectados)
# ---------------------------------------------------------------------
# Mismos nombres de bloque y de campo que las columnas reales de la BD
# (Datos_alimentación_bbdd_Leire_Eduardo/*.csv) — ver README, sección 9.

def crear_estructura_vacia_completa():
    """
    Devuelve el diccionario de datos completo (6 bloques), con todos los
    campos a "". Es el esquema común que deben devolver tanto el motor
    de reglas (src.funciones.extraer_briefing) como el motor LLM
    (src.llm.extraer_briefing_llm) — así son intercambiables desde
    src.nucleo sin cambiar nada más del pipeline.

    Returns:
        dict: Esquema vacío (evento, cliente, espacio, sala, presupuesto,
            ponentes, _aviso_agente, _validacion).
    """
    return {
        "evento": {
            "nombre_evento": "",
            "ciudad": "",
            "lugar_confirmado": "",
            "fecha_inicio": "",
            "fecha_fin": "",
            "numero_personas": "",
            "tipo_evento": "",
            "estado": "",
            "nota": ""
        },
        "cliente": {
            "cliente": "",
            "empresa": "",
            "email": "",
            "telefono": "",
            "sector": "",
            "ciudad": ""
        },
        "espacio": {
            "nombre_espacio": "",
            "ciudad": "",
            "direccion": "",
            "capacidad_total": "",
            "aforo": "",
            "nota": "",
            "telefono_contacto": "",
            "nombre_contacto": "",
            "email_contacto": ""
        },
        "sala": {
            "nombre_sala": "",
            "tipo": "",
            "capacidad_max_sala": "",
            "nota_sala": ""
        },
        "presupuesto": {
            "estado_presupuesto": "",
            "total": "",
            "fecha": "",
            "nota_ubicacion": "",
            "precio_ubicacion": "",
            "precio_catering": "",
            "precio_audiovisuales": "",
            "precio_otros": "",
            "nota_catering": "",
            "nota_audiovisuales": "",
            "nota_otros": "",
            "observaciones": ""
        },
        "ponentes": [],
        "_aviso_agente": {
            "mensaje": "",
            "pestañas_afectadas": []
        },
        "_validacion": {
            "campos_detectados": [],
            "campos_pendientes": [],
            "porcentaje_completado": 0
        }
    }


CAMPOS_OBLIGATORIOS_EVENTO = [
    "nombre_evento",
    "ciudad",
    "fecha_inicio",
    "fecha_fin",
    "numero_personas",
    "tipo_evento"
]


def _fecha_iso_a_visible(fecha_iso: str) -> str:
    """
    Convierte una fecha en ISO (AAAA-MM-DD, el formato en el que
    trabajan internamente los dos motores de extracción -- ver
    src/funciones.py::normalizar_fecha_iso y el prompt del motor LLM)
    a DD/MM/AAAA, el formato pedido por el cliente para la propuesta
    final. Si el valor no es una fecha ISO reconocible (vacío, u otro
    formato ya no estándar), se devuelve tal cual, sin inventar nada.

    Nota importante: a partir de esta conversión, fecha_inicio/
    fecha_fin/fecha YA NO coinciden con el formato real de columnas de
    eventos.csv/presupuestos.csv (que usan AAAA-MM-DD) -- decisión
    explícita del cliente. El orquestador/backend debe reconvertir a
    ISO antes de cualquier INSERT real (ver README.md, sección 11).
    """
    resultado = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", fecha_iso or "")
    if not resultado:
        return fecha_iso or ""
    anio, mes, dia = resultado.groups()
    return f"{dia.zfill(2)}/{mes.zfill(2)}/{anio}"


def generar_aviso_y_validacion(resultado):
    """
    Calcula _aviso_agente (qué pestañas se han cumplimentado) y
    _validacion (% de campos obligatorios detectados) a partir de un
    resultado ya relleno (evento/cliente/espacio/sala/presupuesto/
    ponentes). Común a ambos motores de extracción (reglas y LLM), para
    que el criterio de "completado" no diverja entre ellos.

    También es el único punto por el que pasan SIEMPRE los dos
    motores antes de devolver el resultado -- por eso es aquí, y no en
    cada motor por separado, donde se convierten las fechas de ISO
    (formato interno) a DD/MM/AAAA (formato final pedido por el
    cliente): así no hay que duplicar la conversión ni arriesgarse a
    que un motor la aplique y el otro se quede en ISO por descuido.

    Args:
        resultado (dict): Diccionario con los 6 bloques ya rellenos.

    Returns:
        dict: El mismo resultado, con las fechas en DD/MM/AAAA y con
            _aviso_agente y _validacion añadidos.
    """
    resultado["evento"]["fecha_inicio"] = _fecha_iso_a_visible(resultado["evento"]["fecha_inicio"])
    resultado["evento"]["fecha_fin"] = _fecha_iso_a_visible(resultado["evento"]["fecha_fin"])
    resultado["presupuesto"]["fecha"] = _fecha_iso_a_visible(resultado["presupuesto"]["fecha"])

    pestañas_afectadas = []

    if any(resultado["evento"].values()):
        pestañas_afectadas.append("Evento")
    if any(resultado["cliente"].values()):
        pestañas_afectadas.append("Cliente")
    if any(resultado["espacio"].values()):
        pestañas_afectadas.append("Espacio")
    if any(resultado["sala"].values()):
        pestañas_afectadas.append("Sala")
    if any(resultado["presupuesto"].values()):
        pestañas_afectadas.append("Presupuesto")
    if resultado["ponentes"]:
        pestañas_afectadas.append("Ponentes")

    if pestañas_afectadas:
        if len(pestañas_afectadas) == 1:
            mensaje_aviso = f"Se ha cumplimentado información en la pestaña {pestañas_afectadas[0]}. Requiere validación."
        else:
            pestañas_texto = ", ".join(pestañas_afectadas[:-1]) + " y " + pestañas_afectadas[-1]
            mensaje_aviso = f"Se ha cumplimentado información en las pestañas {pestañas_texto}. Requiere validación."
    else:
        mensaje_aviso = "No se ha podido extraer información del briefing. Por favor, revisa el documento."

    resultado["_aviso_agente"]["mensaje"] = mensaje_aviso
    resultado["_aviso_agente"]["pestañas_afectadas"] = pestañas_afectadas

    campos_detectados = []
    campos_pendientes = []

    for campo in CAMPOS_OBLIGATORIOS_EVENTO:
        if resultado["evento"].get(campo):
            campos_detectados.append(campo)
        else:
            campos_pendientes.append(campo)

    # El porcentaje se calcula solo sobre CAMPOS_OBLIGATORIOS_EVENTO
    # (arriba). Los tres campos siguientes (cliente_nombre,
    # cliente_empresa, espacio_nombre) se muestran también en
    # campos_detectados/campos_pendientes por ser informativos, pero no
    # cuentan en el porcentaje: si contaran en el numerador sin estar en
    # el denominador, el resultado podría superar el 100%.
    detectados_obligatorios = len(campos_detectados)

    if resultado["cliente"].get("cliente"):
        campos_detectados.append("cliente_nombre")
    else:
        campos_pendientes.append("cliente_nombre")

    if resultado["cliente"].get("empresa"):
        campos_detectados.append("cliente_empresa")
    else:
        campos_pendientes.append("cliente_empresa")

    if resultado["espacio"].get("nombre_espacio"):
        campos_detectados.append("espacio_nombre")
    else:
        campos_pendientes.append("espacio_nombre")

    total_obligatorios = len(CAMPOS_OBLIGATORIOS_EVENTO)
    porcentaje = round(detectados_obligatorios / total_obligatorios * 100) if total_obligatorios > 0 else 0

    resultado["_validacion"]["campos_detectados"] = campos_detectados
    resultado["_validacion"]["campos_pendientes"] = campos_pendientes
    resultado["_validacion"]["porcentaje_completado"] = porcentaje

    return resultado
