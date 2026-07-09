"""
Permisos de agente_operis.

Estos valores son NO configurables al alza: aunque .env intentase
activar escritura, en código se fuerzan siempre a False (defensa en
profundidad) — mismo patrón que
Agente_04_Copilot_Raul/lumen_agente_04/config/permisos.py. Operis es un
agente de solo propuesta y esto es una restricción arquitectónica
permanente, no un valor por defecto (ver regla de oro en README.md).
"""

ALLOW_DB_WRITE = False
ALLOW_EXTERNAL_SEND = False
ALLOW_CREATE_EVENT = False
ALLOW_AUTO_APPROVAL = False

# Tablas cuyo esquema de columnas usa agente_operis para nombrar sus
# campos de salida (ver Datos_alimentación_bbdd_Leire_Eduardo/*.csv).
# Operis no CONSULTA estas tablas (no lee BD, ver rag.py) — solo
# reutiliza sus nombres de columna para que su propuesta sea compatible
# con un INSERT directo tras la validación humana.
TABLAS_DE_REFERENCIA = {
    "eventos",
    "clientes",
    "espacios",
    "salas",
    "presupuestos",
    "ponentes",
    "evento_ponente",
}
