"""
Auditoria final de la salida de Lumen - equivalente en codigo a prompts/prompt_validar_salida.md.

Se ejecuta SIEMPRE antes de devolver la respuesta al orquestador, tanto en el flujo determinista
de este demo como (en produccion) sobre la salida del LLM. Es la ultima linea de defensa contra:
  - fuga de la tabla `usuarios` / campo `contrasenia`
  - que Lumen proponga o redacte una accion de escritura (no le corresponde)
"""

PALABRAS_PROHIBIDAS = ["usuarios", "contrasenia", "contraseña", "password"]


def auditar_salida(salida: dict) -> dict:
    # Lumen nunca propone acciones ni redacta borradores: se fuerza siempre, pase lo que pase.
    salida["acciones_propuestas"] = []
    salida["borradores_generados"] = []

    texto = " ".join([
        str(salida.get("resumen", "")),
        str(salida.get("datos_detectados", {})),
    ]).lower()

    if any(palabra in texto for palabra in PALABRAS_PROHIBIDAS):
        salida["resumen"] = "Esa informacion no esta disponible: fuera del alcance de Lumen."
        salida["datos_detectados"] = {}
        salida["nivel_riesgo"] = "alto"
        salida["requiere_validacion_humana"] = True
        mensaje = "fuga bloqueada: referencia a tabla usuarios/credenciales"
        if mensaje not in salida.get("bloqueos_detectados", []):
            salida.setdefault("bloqueos_detectados", []).append(mensaje)

    return salida
