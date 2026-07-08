"""
datos.py — "Base de datos" en memoria (datos de prueba).

Esto simula la base de datos para poder arrancar la API sin PostgreSQL montado.
Cuando la BD real esté lista, se sustituye este módulo por consultas a PostgreSQL,
SIN tocar los endpoints (app.py): ellos solo llaman a estas funciones.

Es decir: este archivo es la ÚNICA pieza que cambia al pasar de mock a BD real.
"""

from datetime import datetime
from copy import deepcopy

# ---------------------------------------------------------------------------
# Datos de prueba iniciales
# ---------------------------------------------------------------------------

_datos = {
    "usuarios": [
        {"id": 1, "nombre": "Admin Demo", "email": "admin@demo.eus",
         "password": "1234", "rol": "admin"},
        {"id": 2, "nombre": "Ane Etxeberria", "email": "ane@tecnalia.eus",
         "password": "1234", "rol": "ponente", "ponente_id": 3},
    ],

    "eventos": [
        {
            "id": 1, "nombre": "Congreso Anual Industria",
            "cliente": "Cámara de Comercio", "tipo": "congreso",
            "num_personas": 320, "fecha_inicio": "2026-07-14",
            "fecha_fin": "2026-07-15", "estado": "pre-evento",
            "lugar_id": 5, "creado_en": "2026-06-30T09:00:00",
        },
        {
            "id": 2, "nombre": "Gala Anual Cámara de Comercio",
            "cliente": "Cámara de Comercio", "tipo": "gala",
            "num_personas": 210, "fecha_inicio": "2026-07-29",
            "fecha_fin": "2026-07-29", "estado": "borrador",
            "lugar_id": None, "creado_en": "2026-07-01T10:30:00",
        },
    ],

    "lugares": [
        {"id": 5, "nombre": "Palacio Kursaal", "zona": "Donostia",
         "capacidad": 600, "valoracion": 4.6,
         "servicios_disponibles": ["catering", "parking", "wifi", "luces", "sonido"]},
        {"id": 6, "nombre": "Teatro Arriaga", "zona": "Bilbao",
         "capacidad": 400, "valoracion": 4.4,
         "servicios_disponibles": ["catering", "terraza", "wifi"]},
        {"id": 7, "nombre": "Europa Biltzar Jauregia", "zona": "Gasteiz",
         "capacidad": 500, "valoracion": 4.2,
         "servicios_disponibles": ["parking", "wifi", "sonido"]},
    ],

    # asignación de lugar a evento (evento_id -> datos)
    "lugares_asignados": [
        {"evento_id": 1, "lugar_id": 5, "fecha_inicio": "2026-07-14",
         "fecha_fin": "2026-07-15", "presupuesto": 6700.00,
         "estado": "confirmado",
         "servicios_incluidos": ["catering", "parking", "wifi"]},
    ],

    "ponentes": [
        {"id": 3, "nombre": "Ane Etxeberria", "empresa": "Tecnalia",
         "cargo": "Investigadora", "email": "ane@tecnalia.eus", "telefono": None},
        {"id": 4, "nombre": "Jon Aguirre", "empresa": "Mondragon",
         "cargo": "Director I+D", "email": "jon@mondragon.eus", "telefono": None},
        {"id": 8, "nombre": "Maite Sánchez", "empresa": "EHU/UPV",
         "cargo": "Catedrática", "email": "maite@ehu.eus", "telefono": None},
    ],

    # relación ponente <-> evento (aquí vive el estado en ese evento)
    "ponentes_evento": [
        {"id": 100, "evento_id": 1, "ponente_id": 3, "rol": "keynote",
         "estado": "confirmado", "documentacion": "completa",
         "ponencia": {"sala": "A", "hora": "10:00"},
         "viajes": "cerrado", "facturacion": "pendiente-pago"},
        {"id": 101, "evento_id": 1, "ponente_id": 4, "rol": "mesa-redonda",
         "estado": "pendiente", "documentacion": "incompleta",
         "ponencia": {"sala": "A", "hora": "12:00"},
         "viajes": "sin-iniciar", "facturacion": "sin-datos"},
        {"id": 102, "evento_id": 1, "ponente_id": 8, "rol": "ponencia",
         "estado": "confirmado", "documentacion": "incompleta",
         "ponencia": {"sala": "B", "hora": "16:00"},
         "viajes": "cerrado", "facturacion": "pagada"},
    ],

    "documentos": [
        {"id": 40, "ponente_id": 3, "tipo": "cv", "estado": "recibido",
         "archivo_url": "/archivos/cv_ane.pdf"},
        {"id": 41, "ponente_id": 3, "tipo": "presentacion", "estado": "en-revision",
         "archivo_url": "/archivos/pres_ane.pdf"},
        {"id": 42, "ponente_id": 4, "tipo": "autorizacion-imagen", "estado": "pendiente",
         "archivo_url": None},
    ],

    "proveedores": [
        {"id": 7, "nombre": "Video y Streaming SL", "tipo": "audiovisual",
         "zona": "Donostia", "valoracion": 4.5},
        {"id": 9, "nombre": "Sonido Pro Euskadi", "tipo": "audiovisual",
         "zona": "Bilbao", "valoracion": 4.3},
        {"id": 11, "nombre": "Azafatas Bidasoa", "tipo": "personal",
         "zona": "Donostia", "valoracion": 4.1},
    ],

    "pedidos": [
        {"id": 12, "evento_id": 1, "proveedor_id": 7,
         "proveedor_nombre": "Video y Streaming SL",
         "necesidades": ["pantalla LED 4x3", "streaming en directo"],
         "estado": "generado", "coste_estimado": 4600.00, "coste_definitivo": None},
    ],

    "presupuestos": [
        {"evento_id": 1, "total_presupuestado": 27000.00,
         "partidas": [
             {"nombre": "Espacio", "presupuestado": 6700.00, "ejecutado": 6160.00},
             {"nombre": "Catering", "presupuestado": 5500.00, "ejecutado": 5500.00},
             {"nombre": "Técnica / AV", "presupuestado": 4600.00, "ejecutado": 5430.00},
             {"nombre": "Viajes", "presupuestado": 4300.00, "ejecutado": 4010.00},
         ]},
    ],

    "borradores": [
        {"id": 21, "evento_id": 1, "ponente_id": 3,
         "tipo": "recordatorio-documentacion",
         "asunto": "Falta tu presentación para el congreso",
         "cuerpo": "Hola Ane, te recordamos que necesitamos tu presentación final...",
         "estado": "pendiente-validacion", "generado_por": "agente-comunicacion"},
    ],

    "bloqueos": [
        {"id": 5, "evento_id": 1, "ponente_id": 4,
         "motivo": "falta-autorizacion-imagen", "gravedad": "alta",
         "detectado_por": "agente-documental"},
    ],
}

# Contador para ids nuevos
_siguiente_id = {"valor": 1000}


def _nuevo_id():
    _siguiente_id["valor"] += 1
    return _siguiente_id["valor"]


# ---------------------------------------------------------------------------
# Funciones de acceso (esto es lo que se sustituye por PostgreSQL en el futuro)
# ---------------------------------------------------------------------------

def listar(tabla):
    """Devuelve una copia de todos los elementos de una tabla."""
    return deepcopy(_datos.get(tabla, []))


def obtener(tabla, id_):
    """Devuelve un elemento por id, o None si no existe."""
    for item in _datos.get(tabla, []):
        if item.get("id") == id_:
            return deepcopy(item)
    return None


def crear(tabla, datos_nuevos):
    """Crea un elemento nuevo con id automático. Devuelve el creado."""
    datos_nuevos = deepcopy(datos_nuevos)
    if "id" not in datos_nuevos or datos_nuevos["id"] is None:
        datos_nuevos["id"] = _nuevo_id()
    _datos.setdefault(tabla, []).append(datos_nuevos)
    return deepcopy(datos_nuevos)


def actualizar(tabla, id_, cambios):
    """Actualiza un elemento por id con los campos de 'cambios'. Devuelve el actualizado o None."""
    for item in _datos.get(tabla, []):
        if item.get("id") == id_:
            item.update(cambios)
            return deepcopy(item)
    return None


def borrar(tabla, id_):
    """Borra un elemento por id. Devuelve True si lo borró."""
    lista = _datos.get(tabla, [])
    for i, item in enumerate(lista):
        if item.get("id") == id_:
            lista.pop(i)
            return True
    return False


def filtrar(tabla, **criterios):
    """Devuelve los elementos que cumplen todos los criterios (campo=valor)."""
    resultado = []
    for item in _datos.get(tabla, []):
        if all(item.get(k) == v for k, v in criterios.items()):
            resultado.append(deepcopy(item))
    return resultado


# ---------------------------------------------------------------------------
# Acceso de solo lectura para agentes de consulta (Lumen — Agente 04 · Copilot)
#
# Lumen es un agente conversacional que responde preguntas del equipo de
# Mitumi sobre los datos de la plataforma. Solo lee, nunca crea, actualiza
# ni borra. Por eso se le expone únicamente esta pareja de funciones, en vez
# de las funciones de escritura de arriba (crear/actualizar/borrar).
# ---------------------------------------------------------------------------

# Tablas visibles para Lumen. Se excluye "usuarios" porque contiene
# credenciales (password) y no aporta nada a preguntas sobre eventos,
# ponentes, lugares, etc.
_TABLAS_CONSULTABLES = [
    "eventos", "lugares", "lugares_asignados", "ponentes", "ponentes_evento",
    "documentos", "proveedores", "pedidos", "presupuestos", "borradores",
    "bloqueos",
]


def tablas_consultables():
    """Lista de tablas que Lumen puede consultar."""
    return list(_TABLAS_CONSULTABLES)


def consultar(tabla=None, **criterios):
    """
    Consulta de solo lectura pensada para Lumen (Agente 04 · Copilot).

    - consultar()                                -> dict con TODAS las tablas consultables
    - consultar("eventos")                       -> lista completa de esa tabla
    - consultar("eventos", estado="pre-evento")  -> lista filtrada por criterios

    Devuelve None si la tabla no existe o no es consultable (p.ej. "usuarios").
    Esta función nunca escribe en los datos.
    """
    if tabla is None:
        return {t: listar(t) for t in _TABLAS_CONSULTABLES}
    if tabla not in _TABLAS_CONSULTABLES:
        return None
    if criterios:
        return filtrar(tabla, **criterios)
    return listar(tabla)
