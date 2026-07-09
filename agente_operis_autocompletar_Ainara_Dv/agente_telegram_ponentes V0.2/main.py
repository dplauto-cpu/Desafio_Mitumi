import json
from pathlib import Path
from src.agente import ejecutar_agente
from src.funciones import guardar_respuesta_json

BASE_DIR = Path(__file__).resolve().parent


def main():
    ruta_payload = BASE_DIR / "inputs" / "payload_demo.json"
    payload = json.loads(ruta_payload.read_text(encoding="utf-8"))

    resultado = ejecutar_agente(payload)

    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    guardar_respuesta_json("ultima_respuesta.json", resultado)


if __name__ == "__main__":
    main()
