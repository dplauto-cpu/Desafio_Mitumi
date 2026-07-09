"""
integrations/api_backend.py — Cliente de SOLO LECTURA para la API real "Proyecto Tripulaciones"
(ERP de Eventos), descrita en el openapi.yaml que aporta el equipo de backend.

Cubre exactamente lo que ese contrato expone: GET /eventos, GET /eventos/{id}, GET /clientes,
GET /clientes/{id}, GET /espacios, GET /espacios/{id}, GET /ponentes, GET /ponentes/{id}.

Limitaciones conocidas de este contrato, importantes para quien use este modulo:

1. Tablas sin endpoint: openapi.yaml no expone salas, presupuestos, estados ni ponencias.
   Esas 4 tablas siguen leyendose de data/mock/*.json (ver src/lectura_datos.py, modo hibrido).
2. IDs UUID vs mock entero: los recursos de esta API usan `id` en formato UUID. Las tablas que
   siguen en mock (salas, presupuestos, estados, ponencias) usan enteros. Si un evento real
   (id UUID) trae un id_sala/id_presupuesto/id_ponencia, ese valor NO va a coincidir con los ids
   enteros del mock hasta que esas tablas tengan su propio endpoint real - contexto_completo_evento
   simplemente no encontrara coincidencia (sala/presupuesto/ponente quedaran a None), no es un bug.
3. Forma de "data": openapi.yaml solo declara "data: object" en el envoltorio comun
   {ok, msg, filters, data}, sin fijar si es una lista directa o un dict que la envuelve. Este
   cliente tolera ambos casos (ver _get) - hay que confirmar el formato real contra la API viva
   y ajustar aqui si difiere.
4. Autenticacion: todos los endpoints exigen Bearer JWT obtenido via POST /auth/login con un
   token de Firebase. Ese login NO lo hace Lumen: se asume un JWT de una cuenta de servicio ya
   emitido y guardado en .env (API_TRIPULACIONES_TOKEN). Si ese token caduca, las llamadas
   fallaran con 401 y se propagara ApiBackendError.
5. Solo lectura reforzada en codigo: aunque la API expone POST/PATCH/DELETE en estos mismos
   recursos, este cliente NO los implementa. Lumen es de solo consulta - igual que con la tabla
   `usuarios`, esto es una restriccion de diseno, no una limitacion tecnica.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from config.settings import API_TRIPULACIONES_BASE_URL, API_TRIPULACIONES_TOKEN


class ApiBackendError(RuntimeError):
    """Fallo de red, autenticacion o formato al llamar a la API real de Tripulaciones."""


def api_disponible() -> bool:
    """True si hay un token configurado en .env (no vacio, no el placeholder de ejemplo)."""
    return bool(API_TRIPULACIONES_TOKEN) and "poner_token" not in API_TRIPULACIONES_TOKEN


def _get(path: str, params: dict = None):
    """
    GET de solo lectura contra la API real. Devuelve el contenido de "data" ya desenvuelto del
    sobre {ok, msg, filters, data}. Devuelve None si el recurso no existe (404). Lanza
    ApiBackendError para cualquier otro fallo (sin token, red caida, 401/403/500, JSON invalido,
    "ok": false) - a diferencia de un 404, esto NO significa "no existe", significa "no se pudo
    saber", y quien llame debe tratarlo como un fallo de infraestructura, no como un dato vacio.
    """
    if not api_disponible():
        raise ApiBackendError(
            "API_TRIPULACIONES_TOKEN no configurado en .env - no se puede llamar a la API real."
        )

    url = API_TRIPULACIONES_BASE_URL.rstrip("/") + path
    if params:
        filtrados = {k: v for k, v in params.items() if v is not None}
        if filtrados:
            url += "?" + urllib.parse.urlencode(filtrados)

    peticion = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + API_TRIPULACIONES_TOKEN,
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(peticion, timeout=10) as resp:
            cuerpo = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise ApiBackendError(
            "La API real de Tripulaciones respondio " + str(exc.code) + " en " + path
        ) from exc
    except urllib.error.URLError as exc:
        raise ApiBackendError(
            "No se pudo conectar a la API real de Tripulaciones en " + url
        ) from exc
    except json.JSONDecodeError as exc:
        raise ApiBackendError(
            "Respuesta no-JSON de la API real de Tripulaciones en " + path
        ) from exc

    if not cuerpo.get("ok", False):
        raise ApiBackendError(cuerpo.get("msg") or "La API real de Tripulaciones devolvio ok=false")

    datos = cuerpo.get("data")
    if isinstance(datos, dict):
        listas = [v for v in datos.values() if isinstance(v, list)]
        if len(listas) == 1:
            return listas[0]
    return datos


def listar_eventos(ciudad=None, tipo_evento=None, estado=None):
    return _get("/eventos", {"ciudad": ciudad, "tipo_evento": tipo_evento, "estado": estado})


def obtener_evento(id_evento):
    return _get("/eventos/" + str(id_evento))


def listar_clientes(sector=None, ciudad=None):
    return _get("/clientes", {"sector": sector, "ciudad": ciudad})


def obtener_cliente(id_cliente):
    return _get("/clientes/" + str(id_cliente))


def listar_espacios(ciudad=None, aforo=None):
    return _get("/espacios", {"ciudad": ciudad, "aforo": aforo})


def obtener_espacio(id_espacio):
    return _get("/espacios/" + str(id_espacio))


def listar_ponentes(sector=None):
    return _get("/ponentes", {"sector": sector})


def obtener_ponente(id_ponente):
    return _get("/ponentes/" + str(id_ponente))
