"""
Acceso de SOLO LECTURA a los datos de Agora para Lumen (Agente 04 - Copilot).

Hoy lee de data/mock/*.json (modo demo). Cuando se conecte integrations/api_backend.py a la
BD real, estas funciones deben apuntar a SELECTs parametrizados equivalentes, nunca a SQL
libre generado por el LLM.

La tabla `usuarios` esta bloqueada aqui a nivel de codigo, no solo por prompt: es defensa en
profundidad ante un fallo del LLM o del orquestador.
"""

import json
from pathlib import Path

from config.permisos import TABLAS_EXCLUIDAS, TABLAS_PERMITIDAS

BASE_DIR = Path(__file__).resolve().parent.parent
MOCK_DIR = BASE_DIR / "data" / "mock"


class TablaNoPermitida(PermissionError):
    """Se lanza si se intenta acceder a una tabla fuera del alcance de Lumen (p.ej. 'usuarios')."""


def tabla_existe(nombre_tabla):
    return nombre_tabla in TABLAS_PERMITIDAS


def _cargar(tabla):
    if tabla in TABLAS_EXCLUIDAS:
        raise TablaNoPermitida("Lumen no tiene acceso a la tabla '" + tabla + "'.")
    if tabla not in TABLAS_PERMITIDAS:
        raise TablaNoPermitida("Tabla '" + tabla + "' fuera del alcance de Lumen.")

    ruta = MOCK_DIR / (tabla + ".json")
    if not ruta.exists():
        return []
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def evento_existe(id_evento):
    for e in _cargar("eventos"):
        if e["id_evento"] == id_evento:
            return True
    return False


def resumen_evento(id_evento):
    """Devuelve el registro de eventos correspondiente, o None si no existe."""
    for e in _cargar("eventos"):
        if e["id_evento"] == id_evento:
            return e
    return None


def ponentes_sin_billete_vuelta(id_evento):
    """
    Devuelve la lista de ponentes (dicts) del evento dado cuyo billete_vuelta_link
    esta vacio. Devuelve None si el evento no existe.
    """
    if not evento_existe(id_evento):
        return None

    ponentes_por_id = {}
    for p in _cargar("ponentes"):
        ponentes_por_id[p["id_ponente"]] = p

    resultado = []
    for ep in _cargar("evento_ponente"):
        if ep["id_evento"] == id_evento and not ep.get("billete_vuelta_link"):
            ponente = ponentes_por_id.get(ep["id_ponente"])
            if ponente:
                resultado.append(ponente)
    return resultado


def ponentes_sin_billete_ida(id_evento):
    """Analogo a ponentes_sin_billete_vuelta pero para el billete de ida."""
    if not evento_existe(id_evento):
        return None

    ponentes_por_id = {}
    for p in _cargar("ponentes"):
        ponentes_por_id[p["id_ponente"]] = p

    resultado = []
    for ep in _cargar("evento_ponente"):
        if ep["id_evento"] == id_evento and not ep.get("billete_ida_link"):
            ponente = ponentes_por_id.get(ep["id_ponente"])
            if ponente:
                resultado.append(ponente)
    return resultado


def estados_disponibles():
    """Lista de descripciones de estado tal como existen en data/mock/estados.json."""
    return [e["descripcion"] for e in _cargar("estados")]


def eventos_por_estado(descripcion_estado):
    """
    Devuelve los eventos (enriquecidos con su descripcion de estado en texto) cuyo id_estado
    corresponde a `descripcion_estado`. Devuelve None si `descripcion_estado` no coincide con
    ningun estado real de estados.json, para que el llamador muestre estados_disponibles() en
    vez de devolver una lista vacia enganosa (que se leeria como "no hay eventos en ese estado"
    cuando en realidad ese estado no existe).
    """
    estados_por_id = {}
    id_estado_buscado = None
    for e in _cargar("estados"):
        estados_por_id[e["id_estado"]] = e["descripcion"]
        if e["descripcion"] == descripcion_estado:
            id_estado_buscado = e["id_estado"]

    if id_estado_buscado is None:
        return None

    resultado = []
    for ev in _cargar("eventos"):
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
    estados_por_id = {e["id_estado"]: e["descripcion"] for e in _cargar("estados")}
    resultado = []
    for ev in _cargar("eventos"):
        enriquecido = dict(ev)
        enriquecido["estado"] = estados_por_id.get(ev.get("id_estado"))
        resultado.append(enriquecido)
    return resultado


def contexto_completo_evento(id_evento):
    """
    Agrega todo el contexto de negocio de un evento (evento, presupuesto, sala, espacio,
    cliente, ponentes) en un unico dict, EXCLUYENDO siempre la tabla `usuarios`.

    Se usa como datos_recuperados para prompts/prompt_generar_respuesta.md: el LLM solo ve
    esto, nunca accede el mismo a la BD, por lo que no puede "decidir" consultar `usuarios`.
    """
    evento = resumen_evento(id_evento)
    if evento is None:
        return None

    presupuesto_encontrado = None
    for p in _cargar("presupuestos"):
        if p["id_evento"] == id_evento:
            presupuesto_encontrado = p
            break

    sala_encontrada = None
    for s in _cargar("salas"):
        if s["id_sala"] == evento.get("id_sala"):
            sala_encontrada = s
            break

    espacio_encontrado = None
    if sala_encontrada:
        for e in _cargar("espacios"):
            if e["id_espacio"] == sala_encontrada.get("id_espacio"):
                espacio_encontrado = e
                break

    cliente_encontrado = None
    for c in _cargar("clientes"):
        if c["id_cliente"] == evento.get("id_cliente"):
            cliente_encontrado = c
            break

    ponentes_por_id = {}
    for p in _cargar("ponentes"):
        ponentes_por_id[p["id_ponente"]] = p

    ponentes_del_evento = []
    for ep in _cargar("evento_ponente"):
        if ep["id_evento"] == id_evento:
            ponente = ponentes_por_id.get(ep["id_ponente"])
            if ponente:
                combinado = dict(ponente)
                combinado.update(ep)
                ponentes_del_evento.append(combinado)

    contexto = {}
    contexto["evento"] = evento
    contexto["presupuesto"] = presupuesto_encontrado
    contexto["sala"] = sala_encontrada
    contexto["espacio"] = espacio_encontrado
    contexto["cliente"] = cliente_encontrado
    contexto["ponentes"] = ponentes_del_evento
    return contexto
