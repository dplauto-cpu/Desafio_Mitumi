"""
rag.py — consulta de contexto histórico/documental. NO APLICA a este
agente: cada extracción es independiente, no consulta histórico de
briefings anteriores ni documentación externa (ver README.md, sección
5.3, y Documentacion_agentes/Agente_OPERIS.md, sección 8.4: "el agente
no mantiene estado ni memoria entre documentos").

Se mantiene como stub (en vez de borrar el archivo) para conservar la
misma estructura interna que otros agentes del proyecto — ver
Agente_04_Copilot_Raul/lumen_agente_04/, que sí usa RAG (data/rag/) por
ser un agente de consulta sobre el histórico de la BD; agente_operis no
lo necesita porque no consulta la BD en absoluto (ver config/permisos.py).
"""


def consultar_contexto(*args, **kwargs):
    """No aplica a este agente — ver docstring del módulo."""
    return None
