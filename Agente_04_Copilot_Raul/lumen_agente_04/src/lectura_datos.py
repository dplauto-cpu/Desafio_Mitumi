"""
Acceso de SOLO LECTURA a los datos de Agora para Lumen (Agente 04 - Copilot).

Modo hibrido (ver config/settings.py, USAR_API_TRIPULACIONES):
- Si esta en False (por defecto): TODO se lee de data/mock/*.json, como en el demo original.
- Si esta en True: eventos, clientes, espacios y ponentes se leen de la API real "Proyecto
  Tripulaciones" (integrations/api_backend.py, ver openapi.yaml). Salas, presupuestos, estados
  y ponencias NO tienen endpoint en esa API todavia, asi que siguen leyendose SIEMPRE de
  data/mock/*.json, este o no activado USAR_API_TRIPULACIONES.

Aviso de tipos en modo API: los ids de la API real son UUID; los ids de las 4 tablas que
siguen en mock son enteros. Si un evento real trae id_sala/id_presupuesto/id_ponencia, ese
valor no coincidira con los ids enteros del mock hasta que esas tablas tengan endpoint propio
- las funciones de este modulo devuelven None/lista vacia en ese caso, no lanzan error.

La tabla `usuarios` esta bloqueada aqui a nivel de codigo, no solo por prompt: es defensa en
profundidad ante un fallo del LLM o del orquestador. Este bloqueo aplica igual en modo mock y
en modo API - `usuarios` nunca se pide a ninguna de las dos fuentes.
"""

import json
from pathlib import Path

from config.permisos import TABLAS_EXCLUIDAS, TABLAS_PERMITIDAS
from config.settings import USAR_API_TRIPULACIONES
from integrations import api_backend

BASE_DIR = Path(__file__).resolve().parent.parent
MOCK_DIR = BASE_DIR / "data" / "mock"

# Tablas que, con USAR_API_TRIPULACIONES=True, se leen de la API real en vez del mock.
TABLAS_VIA_API = {"eventos", "clientes", "espacios", "ponentes"}


class TablaNoPermitida(PermissionError):
    """Se lanza si se intenta acceder a una tabla fuera del alcance de Lumen (p.ej. 'usuarios')."""


def tabla_existe(nombre_tabla):
    return nombre_tabla in TABLAS_PERMITIDAS


def _via_api(tabla):
    return USAR_API_TRIPULACIONES and tabla in TABLAS_VIA_API


def _cargar(tabla):
    """Carga TODOS los registros de una tabla desde el mock JSON (nunca desde la API real)."""
    if tabla in TABLAS_EXCLUIDAS:
        raise TablaNoPermitida("Lumen no tiene acceso a la tabla '" + tabla + "'.")
    if tabla not in TABLAS_PERMITIDAS:
        raise TablaNoPermitida("Tabla '" + tabla + "' fuera del alcance de Lumen.")

    ruta = MOCK_DIR / (tabla + ".json")
    if not ruta.exists():
        return []
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def _verificar_permiso(tabla):
    if tabla in TABLAS_EXCLUIDAS:
        raise TablaNoPermitida("Lumen no tiene acceso a la tabla '" + tabla + "'.")
    if tabla not in TABLAS_PERMITIDAS:
        raise TablaNoPermitida("Tabla '" + tabla + "' fuera del alcance de Lumen.")


def evento_existe(id_evento):
    return resumen_evento(id_evento) is not None


def resumen_evento(id_evento):
    """Devuelve el registro de eventos correspondiente, o None si no existe."""
    _verificar_permiso("eventos")
    if _via_api("eventos"):
        return api_backend.obtener_evento(id_evento)
    for e in _cargar("eventos"):
        if e["id"] == id_evento:
            return e
    return None


def _ponente_por_id(id_ponente):
    if id_ponente is None:
        return None
    _verificar_permiso("ponentes")
    if _via_api("ponentes"):
        return api_backend.obtener_ponente(id_ponente)
    for p in _cargar("ponentes"):
        if p["id"] == id_ponente:
            return p
    return None


def _ponencia_del_evento(evento):
    """
    Devuelve la ponencia enlazada al evento (via eventos.id_ponencia), o None si el evento no
    tiene ninguna ponencia asociada. `ponencias` no tiene endpoint en la API real: siempre se
    lee del mock, aunque el evento venga de la API (ver aviso de tipos en la cabecera).
    """
    id_ponencia = evento.get("id_ponencia")
    if id_ponencia is None:
        return None
    for pc in _cargar("ponencias"):
        if pc["id"] == id_ponencia:
            return pc
    return None


def ponentes_sin_billete_vuelta(id_evento):
    """
    Devuelve la lista de ponentes (dicts) del evento dado cuyo billete_vuelta_link
    esta vacio. Devuelve None si el evento no existe. Con el esquema actual la lista
    contendra como mucho un elemento (un evento enlaza con una unica ponencia/ponente).
    """
    evento = resumen_evento(id_evento)
    if evento is None:
        return None

    ponencia = _ponencia_del_evento(evento)
    if ponencia is None or ponencia.get("billete_vuelta_link"):
        return []

    ponente = _ponente_por_id(ponencia.get("id_ponente"))
    return [ponente] if ponente else []


def ponentes_sin_billete_ida(id_evento):
    """Analogo a ponentes_sin_billete_vuelta pero para el billete de ida."""
    evento = resumen_evento(id_evento)
    if evento is None:
        return None

    ponencia = _ponencia_del_evento(evento)
    if ponencia is None or ponencia.get("billete_ida_link"):
        return []

    ponente = _ponente_por_id(ponencia.get("id_ponente"))
    return [ponente] if ponente else []


def estados_disponibles():
    """Lista de descripciones de estado tal como existen en data/mock/estados.json. Sin
    endpoint en la API real: siempre se lee del mock."""
    return [e["descripcion"] for e in _cargar("estados")]


def eventos_por_estado(descripcion_estado):
    """
    Devuelve los eventos (enriquecidos con su descripcion de estado en texto) cuyo id_estado
    corresponde a `descripcion_estado`. Devuelve None si `descripcion_estado` no coincide con
    ningun estado real de estados.json, para que el llamador muestre estados_disponibles() en
    vez de devolver una lista vacia enganosa.

    Nota modo API: si USAR_API_TRIPULACIONES esta activo, los eventos vienen de la API real
    (id_estado en el formato que use esa API) y se cruzan igualmente contra estados.json (mock,
    ids enteros) - si no coinciden, el evento simplemente no se etiquetara con un estado legible.
    """
    estados_por_id = {}
    id_estado_buscado = None
    for e in _cargar("estados"):
        estados_por_id[e["id"]] = e["descripcion"]
        if e["descripcion"] == descripcion_estado:
            id_estado_buscado = e["id"]

    if id_estado_buscado is None:
        return None

    _verificar_permiso("eventos")
    eventos = api_backend.listar_eventos() if _via_api("eventos") else _cargar("eventos")
    resultado = []
    for ev in eventos or []:
        if ev.get("id_estado") == id_estado_buscado:
            enriquecido = dict(ev)
            enriquecido["estado"] = estados_por_id.get(ev.get("id_estado"))
            resultado.append(enriquecido)
    return resultado


def todos_los_eventos():
    """
    Devuelve todos los eventos, cada uno con su 'estado' ya resuelto a texto (a partir de
    estados.json). Se usa para consultas transversales generales ("cuantos eventos hay",
    "listame los eventos") que no filtran por un estado concreto.
    """
    estados_por_id = {e["id"]: e["descripcion"] for e in _cargar("estados")}
    _verificar_permiso("eventos")
    eventos = api_backend.listar_eventos() if _via_api("eventos") else _cargar("eventos")
    resultado = []
    for ev in eventos or []:
        enriquecido = dict(ev)
        enriquecido["estado"] = estados_por_id.get(ev.get("id_estado"))
        resultado.append(enriquecido)
    return resultado


def contexto_completo_evento(id_evento):
    """
    Agrega todo el contexto de negocio de un evento (evento, presupuesto, sala, espacio,
    cliente, ponente via su ponencia) en un unico dict, EXCLUYENDO siempre la tabla `usuarios`.

    presupuesto, sala y ponencia siempre salen del mock (sin endpoint real). cliente y espacio
    salen de la API real cuando USAR_API_TRIPULACIONES esta activo.
    """
    evento = resumen_evento(id_evento)
    if evento is None:
        return None

    presupuesto_encontrado = None
    for p in _cargar("presupuestos"):
        if p["id"] == evento.get("id_presupuesto"):
            presupuesto_encontrado = p
            break

    sala_encontrada = None
    for s in _cargar("salas"):
        if s["id"] == evento.get("id_sala"):
            sala_encontrada = s
            break

    espacio_encontrado = None
    if sala_encontrada:
        id_espacio = sala_encontrada.get("id_espacio")
        _verificar_permiso("espacios")
        if _via_api("espacios"):
            espacio_encontrado = api_backend.obtener_espacio(id_espacio)
        else:
            for e in _cargar("espacios"):
                if e["id"] == id_espacio:
                    espacio_encontrado = e
                    break

    cliente_encontrado = None
    id_cliente = evento.get("id_cliente")
    _verificar_permiso("clientes")
    if _via_api("clientes"):
        cliente_encontrado = api_backend.obtener_cliente(id_cliente)
    else:
        for c in _cargar("clientes"):
            if c["id"] == id_cliente:
                cliente_encontrado = c
                break

    ponencia_encontrada = _ponencia_del_evento(evento)
    ponentes_del_evento = []
    if ponencia_encontrada is not None:
        ponente = _ponente_por_id(ponencia_encontrada.get("id_ponente"))
        if ponente:
            combinado = dict(ponente)
            combinado.update(ponencia_encontrada)
            ponentes_del_evento.append(combinado)

    contexto = {}
    contexto["evento"] = evento
    contexto["presupuesto"] = presupuesto_encontrado
    contexto["sala"] = sala_encontrada
    contexto["espacio"] = espacio_encontrado
    contexto["cliente"] = cliente_encontrado
    contexto["ponentes"] = ponentes_del_evento
    return contexto
