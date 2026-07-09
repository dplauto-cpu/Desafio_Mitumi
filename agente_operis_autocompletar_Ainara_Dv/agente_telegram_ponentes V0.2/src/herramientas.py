from integrations.api_backend import (
    obtener_ponente_por_telegram,
    obtener_eventos_activos_ponente,
    obtener_info_ponente_evento,
    registrar_comunicacion,
    crear_incidencia,
)

# Este archivo agrupa las herramientas propias del agente.
# El LLM no llama directamente a estas funciones: Python controla el flujo.
