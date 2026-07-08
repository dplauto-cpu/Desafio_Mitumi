"""Persistencia en SQLite para evitar procesar dos veces la misma convocatoria."""

# traigo sqlite3 para trabajar con la base de datos local
import sqlite3
# traigo contextmanager para crear un "with" que abre y cierra la conexión solo
from contextlib import contextmanager
# traigo Iterator para anotar bien el tipo que devuelve el context manager
from typing import Iterator

# escribo la orden que crea la tabla de convocatorias procesadas si no existe
_SCHEMA = """
CREATE TABLE IF NOT EXISTS procesados (
    id_expediente TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    procesado_en TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


# marco esta función como un context manager para usarla con "with"
@contextmanager
def get_connection(db_path: str) -> Iterator[sqlite3.Connection]:
    # abro la conexión con el fichero de base de datos
    conn = sqlite3.connect(db_path)
    # intento usar la conexión y me aseguro de cerrarla al final
    try:
        # creo la tabla si todavía no existía
        conn.execute(_SCHEMA)
        # confirmo (guardo) ese cambio
        conn.commit()
        # entrego la conexión a quien la pidió con el "with"
        yield conn
    # pase lo que pase, cierro la conexión al terminar
    finally:
        conn.close()


# compruebo si una convocatoria ya se procesó antes
def ya_procesado(conn: sqlite3.Connection, id_expediente: str) -> bool:
    # busco en la tabla una fila con ese id de expediente
    cur = conn.execute(
        "SELECT 1 FROM procesados WHERE id_expediente = ?", (id_expediente,)
    )
    # devuelvo True si encontré algo, False si no encontré nada
    return cur.fetchone() is not None


# apunto una convocatoria como ya procesada
def marcar_procesado(conn: sqlite3.Connection, id_expediente: str, url: str) -> None:
    # inserto la fila; si ya existía ese id, no hago nada (INSERT OR IGNORE)
    conn.execute(
        "INSERT OR IGNORE INTO procesados (id_expediente, url) VALUES (?, ?)",
        (id_expediente, url),
    )
    # confirmo (guardo) el cambio en el fichero
    conn.commit()
