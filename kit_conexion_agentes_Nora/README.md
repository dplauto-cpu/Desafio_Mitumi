# Kit de conexión de agentes a la BBDD real (Neon)

Para cualquier agente de data que necesite **leer** datos reales. Es el mismo patrón que ya
usa Lumen en producción (`Agente_04_Copilot_Raul/lumen_agente_04/integrations/bd_backend.py`),
extraído como plantilla. Tiempo estimado: **10 minutos**.

## Reglas antes de empezar (no negociables)

1. **Solo lectura.** Se usa el rol `agente_readonly` — Postgres rechaza cualquier escritura
   y no ve la tabla `usuarios`. Pídele la cadena de conexión a Nora. **Nunca** uses la
   cadena de `neondb_owner` en un agente.
2. **La cadena va en tu `.env`, y tu `.env` NUNCA se sube a git** (comprueba tu .gitignore).
3. **El LLM jamás escribe SQL.** Tus consultas son funciones Python fijas y parametrizadas;
   el LLM solo ve los resultados.
4. Escribir en la BBDD (borradores, incidencias…): **por el backend, nunca directo** —
   es la regla de oro del proyecto (contrato v3, §6).

## Pasos

1. Copia `bd_backend.py` a la carpeta `integrations/` (o equivalente) de tu agente.
2. Edita su lista `_TABLAS_BD` dejando SOLO las tablas que tu agente necesita.
3. Añade a tu `.env`:
   ```env
   DATABASE_URL=postgresql://agente_readonly:<pedir-a-nora>@ep-autumn-wildflower-ass2epey-pooler.c-4.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
4. Instala el driver: `pip install "psycopg[binary]"` (añádelo a tu requirements).
5. Verifica: `python3 test_conexion.py` desde la carpeta de tu agente (o pasándole la ruta
   del `.env`). Debe salir todo PASS.
6. En tu código: `from integrations.bd_backend import leer_tabla` → `leer_tabla("eventos")`
   devuelve la lista de dicts con UUIDs como strings y fechas como `AAAA-MM-DD`.

## Datos que debes conocer (estado a 10-jul)

- Ids **UUID** (strings). Estados de evento: Borrador, Presupuestado, Pendiente de aprobación,
  Confirmado, En ejecución, Celebrado, Facturado, Cancelado — compara **sin distinguir
  mayúsculas**.
- `eventos.id_sala` e `id_ponencia` están a NULL hasta que BBDD ejecute el script de enlace
  (`Datos_alimentación_bbdd_Leire_Eduardo/enlace_bbdd/`). Tu código debe tolerar esos NULL.
- La relación evento↔ponente va por `eventos.id_ponencia → ponencias → ponentes`
  (un solo ponente por evento, limitación del esquema ya reportada a backend).

## Vistas SQL (opcional, recomendado a futuro)

`sql/vistas_agentes.sql` crea vistas estables (`vista_agente_eventos`, etc.) para que si
backend renombra columnas, los agentes no se rompan. Las aplica el equipo de BBDD cuando
lo decida — los agentes pueden usar las tablas directamente mientras tanto.
