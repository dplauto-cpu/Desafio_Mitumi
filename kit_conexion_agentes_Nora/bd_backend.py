"""
bd_backend.py — PLANTILLA de acceso de SOLO LECTURA a la BBDD real (Neon Postgres).

Cópiala a integrations/ de tu agente y edita _TABLAS_BD (deja solo lo que necesites).
Es el mismo patrón que usa Lumen en producción. Ver README.md del kit.

Defensas incluidas (no las quites):
- Lista blanca de tablas: el nombre de tabla NUNCA viene del LLM ni del usuario.
- Conexión marcada read-only: aunque la credencial permitiera escribir, Postgres lo rechaza.
- El rol agente_readonly ademas no tiene GRANT sobre `usuarios` (tercera capa, en la BBDD).
- Tipos normalizados (UUID→str, timestamps de medianoche→AAAA-MM-DD, Decimal→float) para
  que las filas sean serializables con json.dumps y comparables con mocks.
"""

import datetime
import decimal
import os
import uuid

import psycopg
from psycopg.rows import dict_row

# Si tu agente carga settings desde .env, importa desde ahí en su lugar.
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# EDITA ESTA LISTA: deja solo las tablas que tu agente necesita leer.
_TABLAS_BD = {
    "clientes", "eventos", "presupuestos", "ponentes",
    "ponencias", "estados", "salas", "espacios",
}


class BdBackendError(RuntimeError):
    """Fallo de conexion o consulta contra la BD real."""


def bd_disponible() -> bool:
    return bool(DATABASE_URL)


def _normalizar_valor(v):
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, datetime.datetime):
        return v.date().isoformat() if v.time() == datetime.time(0, 0) else v.isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    return v


def leer_tabla(tabla: str) -> list:
    """SELECT * de una tabla de la lista blanca, como lista de dicts serializables."""
    if tabla not in _TABLAS_BD:
        raise BdBackendError("Tabla '" + tabla + "' fuera de la lista blanca de BD.")
    if not bd_disponible():
        raise BdBackendError("DATABASE_URL no configurada en .env.")

    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=10, row_factory=dict_row) as conn:
            conn.read_only = True
            filas = conn.execute('SELECT * FROM "' + tabla + '"').fetchall()
    except psycopg.Error as exc:
        raise BdBackendError("No se pudo leer la tabla '" + tabla + "' de la BD real.") from exc

    return [{k: _normalizar_valor(v) for k, v in fila.items()} for fila in filas]
