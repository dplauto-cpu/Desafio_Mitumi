"""
servidor.py — API HTTP de Lumen (Agente 04 - Copilot) para el frontend React.

Expone el chat de Lumen por HTTP, con memoria de conversacion por sesion (ver src/memoria.py).
No sustituye el contrato de integracion real del proyecto (ejecutar_agente(payload) en
src/agente.py, que sigue siendo lo que usaria el orquestador) -- esta es una capa pensada
especificamente para que el frontend React pueda mandar preguntas y recibir respuestas en JSON,
con memoria conversacional igual que main.py, pero por sesion de navegador en vez de por
proceso de consola.

Arrancar:
    cd lumen_agente_04
    pip install -r requirements.txt
    python servidor.py

Por defecto escucha en http://localhost:5001 (puerto distinto del mock de API_Nora, que usa
el 5000, para poder tener ambos arrancados a la vez).

Endpoints:
    GET  /              -> estado del servidor (health check)
    POST /chat           -> body: {"sesion_id": "..." (opcional), "pregunta": "..."}
                             Si no se manda sesion_id (o no existe todavia), se crea una nueva y
                             se devuelve en la respuesta -- el frontend debe guardarla (p.ej. en
                             el estado de React) y reenviarla en las siguientes peticiones de esa
                             misma conversacion para conservar la memoria.
    POST /chat/reset      -> body: {"sesion_id": "..."} -> olvida el contexto de esa sesion.

Nota de seguridad/alcance: las sesiones viven SOLO en memoria del proceso (un dict de Python).
Si el servidor se reinicia, todas las conversaciones en curso se pierden. Es una limitacion
aceptada para esta fase de demo -- no es un almacen productivo ni persistente. Cuando haya un
backend real, esto se sustituye por sesiones respaldadas por ese backend (Redis, BD, etc.), sin
tocar src/agente.py ni src/memoria.py.
"""

import sys
import uuid
from pathlib import Path

from flask import Flask, request, jsonify

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))  # permite "from src.agente import ..." y "from config import ..."

from src.agente import ejecutar_agente  # noqa: E402
from src.memoria import MemoriaConversacion, construir_payload  # noqa: E402

app = Flask(__name__)

# CORS: permite que el frontend React (otro puerto, p.ej. localhost:3000) llame a esta API desde
# el navegador. Sin esto, el navegador bloquea las peticiones aunque el servidor si responda.
try:
    from flask_cors import CORS
    CORS(app)
except ImportError:
    print("Aviso: flask-cors no instalado. El frontend en el navegador puede fallar por CORS.")

# Memoria de conversacion por sesion (sesion_id -> MemoriaConversacion). Vive solo en RAM del
# proceso -- ver nota de seguridad/alcance en la cabecera del archivo.
_sesiones = {}


def _obtener_memoria(sesion_id):
    if sesion_id not in _sesiones:
        _sesiones[sesion_id] = MemoriaConversacion()
    return _sesiones[sesion_id]


def _error(codigo, mensaje, http=400):
    return jsonify({"error": True, "codigo": codigo, "mensaje": mensaje}), http


@app.get("/")
def inicio():
    return jsonify({
        "servicio": "Lumen - Agente 04 - Copilot",
        "estado": "en marcha",
        "sesiones_activas": len(_sesiones),
        "prueba": 'POST /chat con {"pregunta": "..."}',
    })


@app.post("/chat")
def chat():
    cuerpo = request.get_json(silent=True) or {}
    pregunta = (cuerpo.get("pregunta") or "").strip()

    if not pregunta:
        return _error("PREGUNTA_VACIA", "Falta el campo 'pregunta'.")

    sesion_id = cuerpo.get("sesion_id") or str(uuid.uuid4())
    memoria = _obtener_memoria(sesion_id)

    id_evento, _usando_memoria = memoria.resolver_id_evento(pregunta)
    payload = construir_payload(
        id_evento, memoria.historial_para_payload(), pregunta, origen="frontend_react"
    )

    respuesta = ejecutar_agente(payload)
    memoria.registrar_turno(pregunta, respuesta, id_evento)

    return jsonify({
        "sesion_id": sesion_id,
        "resumen": respuesta.get("resumen", ""),
        "bloqueos_detectados": respuesta.get("bloqueos_detectados", []),
        "requiere_validacion_humana": respuesta.get("requiere_validacion_humana", False),
        "nivel_riesgo": respuesta.get("nivel_riesgo", "bajo"),
        "datos_detectados": respuesta.get("datos_detectados", {}),
        # Estado de memoria DESPUES de este turno -- util para que el frontend muestre algo tipo
        # "hablando del evento 12" de forma persistente, no solo en el turno que lo detecto.
        "id_evento_actual": memoria.id_evento_actual,
        "errores": respuesta.get("errores", []),
    })


@app.post("/chat/reset")
def chat_reset():
    cuerpo = request.get_json(silent=True) or {}
    sesion_id = cuerpo.get("sesion_id")

    if not sesion_id:
        return _error("FALTA_SESION_ID", "Falta el campo 'sesion_id'.")

    if sesion_id in _sesiones:
        _sesiones[sesion_id].reiniciar()

    return jsonify({"ok": True, "sesion_id": sesion_id})


@app.errorhandler(404)
def no_encontrado(e):
    return _error("RUTA_NO_ENCONTRADA", "Esa ruta no existe.", 404)


if __name__ == "__main__":
    # debug=True recarga solo al guardar cambios (comodo mientras desarrollais)
    app.run(debug=True, port=5001)
