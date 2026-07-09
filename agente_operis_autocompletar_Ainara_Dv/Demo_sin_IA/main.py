"""
main.py — punto de entrada único de agente_operis para uso local.

Uso:
    python main.py --demo                       -> un solo disparo sobre
                                                     inputs/payload_demo.json
                                                     (regresión/prueba
                                                     reproducible), guarda la
                                                     salida en
                                                     outputs/respuestas_json/salida_demo.json
    python main.py ruta/al/briefing.txt          -> procesa un archivo cualquiera
                                                     (.txt/.pdf/.docx), con el motor de
                                                     OPERIS_MOTOR en .env (por defecto
                                                     "reglas" si no hay .env)
    python main.py ruta/al/briefing.txt --motor llm
                                                  -> igual, forzando el motor LLM (Groq)
    python main.py ruta/al/briefing.txt --motor reglas
                                                  -> igual, forzando el motor de reglas

Nota: esto es solo para pruebas/uso local en consola. ejecutar_agente(payload)
en src/agente.py sigue siendo el único contrato de integración real
(README.md, sección 9) — mismo principio que
Agente_04_Copilot_Raul/lumen_agente_04/main.py.
"""

import json
import sys
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))  # permite "from src.agente import ..." y "from config import ..."

from src.agente import ejecutar_agente  # noqa: E402
from src import funciones  # noqa: E402
from config import settings  # noqa: E402


def construir_payload(texto_briefing: str, motor: str) -> dict:
    """Construye un payload mínimo válido (ver src/validaciones.py) para pruebas manuales."""
    return {
        "id_evento": None,
        "id_registro": None,
        "tipo_peticion": "extraer_briefing",
        "origen": "manual",
        "usuario_solicitante": "cli",
        "rol_usuario": "organizador",
        "datos": {
            "texto_briefing": texto_briefing,
            "motor": motor
        },
        "contexto": {},
        "modo": "propuesta"
    }


def modo_demo():
    """Un solo disparo sobre inputs/payload_demo.json."""
    payload_path = BASE_DIR / "inputs" / "payload_demo.json"
    output_dir = BASE_DIR / "outputs" / "respuestas_json"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    print("--- Payload de entrada ---")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    respuesta = ejecutar_agente(payload)

    print("\n--- Respuesta de agente_operis ---")
    print(json.dumps(respuesta, ensure_ascii=False, indent=2))

    ruta_salida = output_dir / "salida_demo.json"

    if ruta_salida.exists():
        with open(ruta_salida, "r", encoding="utf-8") as f:
            referencia = json.load(f)
        # Ignoramos "trazas.timestamp": cambia en cada ejecución por diseño.
        comparable_actual = {k: v for k, v in respuesta.items() if k != "trazas"}
        comparable_ref = {k: v for k, v in referencia.items() if k != "trazas"}
        if comparable_actual == comparable_ref:
            print("\n[OK] Coincide con outputs/respuestas_json/salida_demo.json (motor reglas, determinista).")
        else:
            print("\n[DIFERENCIA] No coincide con salida_demo.json — revisar antes de subir.")

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(respuesta, f, ensure_ascii=False, indent=2)

    print(f"\nRespuesta guardada en: {ruta_salida}")


def modo_archivo(ruta_archivo: str, motor: str):
    """Procesa un archivo cualquiera pasado por línea de comandos."""
    print("=" * 70)
    print("AGENTE OPERIS - EXTRACCIÓN DE BRIEFING")
    print("=" * 70)
    print(f"Archivo: {ruta_archivo}")
    print(f"Motor: {motor}")
    print("-" * 70)

    try:
        texto = funciones.leer_archivo(ruta_archivo)
    except Exception as e:
        print(f"ERROR al leer el archivo: {e}")
        return

    payload = construir_payload(texto, motor)
    respuesta = ejecutar_agente(payload)

    if not respuesta["ok"]:
        print(f"ERROR: {'; '.join(respuesta['errores'])}")
        return

    print("\nRESPUESTA DEL AGENTE (contrato con el orquestador):")
    print("-" * 70)
    print(json.dumps(respuesta, ensure_ascii=False, indent=2))

    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Resumen: {respuesta['resumen']}")
    evento = respuesta["datos_detectados"].get("evento", {})
    fecha_inicio = evento.get("fecha_inicio", "")
    fecha_fin = evento.get("fecha_fin", "")
    if fecha_inicio or fecha_fin:
        if fecha_inicio == fecha_fin:
            print(f"Fecha del evento: {fecha_inicio}")
        else:
            print(f"Fechas del evento: {fecha_inicio} - {fecha_fin}")
    if respuesta["bloqueos_detectados"]:
        print(f"Campos pendientes: {', '.join(respuesta['bloqueos_detectados'])}")
    else:
        print("Todos los campos obligatorios han sido detectados.")
    print(f"requiere_validacion_humana: {respuesta['requiere_validacion_humana']}")
    print(f"nivel_riesgo: {respuesta['nivel_riesgo']}")


def main():
    parser = argparse.ArgumentParser(
        description="agente_operis — extracción de briefings de eventos (uso local)."
    )
    parser.add_argument("archivo", nargs="?", default=None, help="Ruta al briefing (.txt/.pdf/.docx)")
    parser.add_argument("--motor", choices=["reglas", "llm"], default=settings.MOTOR_POR_DEFECTO,
                         help="Motor de extracción: 'reglas' (gratis) o 'llm' (Groq, requiere GROQ_API_KEY). "
                              f"Por defecto usa OPERIS_MOTOR de .env (aquí: '{settings.MOTOR_POR_DEFECTO}').")
    parser.add_argument("--demo", action="store_true", help="Ejecuta inputs/payload_demo.json")
    args = parser.parse_args()

    if args.demo or not args.archivo:
        modo_demo()
    else:
        modo_archivo(args.archivo, args.motor)


if __name__ == "__main__":
    main()
