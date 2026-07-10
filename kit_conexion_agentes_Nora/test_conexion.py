"""
test_conexion.py — Verifica que tu agente puede leer la BBDD real y que las defensas funcionan.

Uso (desde la carpeta de tu agente, donde está tu .env):
    python3 ruta/al/kit_conexion_agentes/test_conexion.py
o indicando el .env:
    python3 test_conexion.py /ruta/a/mi/.env

Comprueba: conexión, lectura de las 8 tablas de negocio, que `usuarios` está bloqueada
y que escribir es imposible. Todo PASS = tu agente puede conectarse con seguridad.
"""

import os
import sys
from pathlib import Path

import psycopg


def cargar_env(ruta):
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, _, valor = linea.partition("=")
            os.environ.setdefault(clave.strip(), valor.strip())


def main():
    ruta_env = sys.argv[1] if len(sys.argv) > 1 else ".env"
    if Path(ruta_env).exists():
        cargar_env(ruta_env)

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit("FALLO: no hay DATABASE_URL (ni en el entorno ni en " + ruta_env + ")")
    if "neondb_owner" in url:
        sys.exit("FALLO: estás usando la cadena del OWNER. Los agentes usan agente_readonly.")

    fallos = 0
    try:
        conn = psycopg.connect(url, connect_timeout=15)
    except psycopg.Error as e:
        sys.exit(f"FALLO: no se pudo conectar — {e}")
    print("PASS  conexión establecida (rol readonly)")

    with conn, conn.cursor() as cur:
        for tabla in ("clientes", "eventos", "presupuestos", "ponentes",
                      "ponencias", "estados", "salas", "espacios"):
            try:
                cur.execute(f'SELECT count(*) FROM "{tabla}"')
                print(f"PASS  lectura de {tabla}: {cur.fetchone()[0]} filas")
            except psycopg.Error:
                conn.rollback()
                print(f"FALLO lectura de {tabla}")
                fallos += 1

        try:
            cur.execute("SELECT * FROM usuarios LIMIT 1")
            print("FALLO la tabla usuarios ES accesible (no debería)")
            fallos += 1
        except psycopg.Error:
            conn.rollback()
            print("PASS  usuarios bloqueada por Postgres")

        try:
            cur.execute("UPDATE eventos SET nota = nota WHERE false")
            print("FALLO el rol PUEDE escribir (no debería)")
            fallos += 1
        except psycopg.Error:
            conn.rollback()
            print("PASS  escritura bloqueada por Postgres")

    print("\nRESULTADO:", "TODO PASS — tu agente puede conectarse ✅" if fallos == 0
          else f"{fallos} comprobaciones fallaron — revisa antes de conectar tu agente")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
