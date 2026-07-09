"""
Punto de entrada común de agente_operis.

Este es el nombre de fichero y función OBLIGATORIOS según el contrato
del proyecto (README.md, sección 9): src/agente.py debe exponer
ejecutar_agente(payload) -> dict, sin excepción.

La implementación real vive en src/nucleo.py (validación, elección de
motor, construcción de la salida) y src/funciones.py / src/llm.py (los
dos motores de extracción). Este archivo es solo el punto de entrada
estable que el orquestador, main.py o una futura API deben poder
importar siempre igual — mismo patrón que
Agente_04_Copilot_Raul/lumen_agente_04/src/agente.py.
"""

from src.nucleo import ejecutar_agente

__all__ = ["ejecutar_agente"]
