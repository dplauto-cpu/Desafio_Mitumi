"""
memoria.py — Memoria de conversacion de Lumen (Agente 04 - Copilot).

Capa POR ENCIMA de ejecutar_agente(payload), sin tocar su contrato (README.md, seccion 1, lo
marca como no modificable porque el orquestador depende de que siga siendo stateless). Tanto
main.py (chat de consola) como servidor.py (API HTTP para el frontend React) usan esta misma
clase, cada uno con sus propias instancias:

  - main.py:      una MemoriaConversacion para toda la sesion de consola.
  - servidor.py:  una MemoriaConversacion POR sesion de chat del navegador (session_id),
                   guardadas en un diccionario en memoria del proceso Flask.

Qué hace la memoria:
  1. Recuerda el ultimo id_evento del que se hablo, y permite reutilizarlo cuando la siguiente
     pregunta no especifica un evento y no es una consulta transversal (p.ej. "¿y su
     presupuesto?" despues de preguntar por el evento 12).
  2. Se "engancha" tambien al id_evento cuando una consulta transversal ("cuantos eventos
     tenemos", "que eventos hay en marcha") devuelve EXACTAMENTE un evento -- para que un
     "ese evento" en el turno siguiente funcione sin repetir el numero. Si devuelve varios,
     no se adivina cual.
  3. Guarda un historial corto (ultimos MAX_TURNOS_HISTORIAL turnos) que se pasa en
     payload["contexto"]["historial_conversacion"] -- ese campo ya existia en el contrato de
     payload, aqui solo se rellena. src/nucleo.py lo reenvia al LLM (Groq) unicamente para
     resolver referencias del lenguaje, nunca como fuente de datos nueva.

La memoria vive solo en memoria de proceso (RAM): no se guarda en disco ni sobrevive a un
reinicio del proceso (de main.py o de servidor.py). Es una decision consciente, no una
limitacion a resolver despues.
"""

import re

from src.nucleo import _parece_consulta_transversal_eventos

MAX_TURNOS_HISTORIAL = 6


class MemoriaConversacion:
    def __init__(self):
        self.id_evento_actual = None
        self.historial = []  # [{"pregunta": ..., "resumen": ...}, ...]

    def reiniciar(self):
        self.id_evento_actual = None
        self.historial = []

    def historial_para_payload(self):
        return list(self.historial[-MAX_TURNOS_HISTORIAL:])

    def resolver_id_evento(self, pregunta):
        """
        Decide que id_evento usar para este turno, antes de llamar a ejecutar_agente:
        - si la pregunta lo dice explicitamente ("evento 12"), se usa ese, sin tocar memoria.
        - si no lo dice pero parece una consulta transversal (varios eventos, conteos, por
          estado...), se deja en None a proposito para que ejecutar_agente la trate como tal.
        - si no lo dice y NO es transversal, se reutiliza el ultimo evento recordado (si hay).
        Devuelve (id_evento, usando_memoria: bool).
        """
        explicito = _extraer_id_evento_explicito(pregunta)
        if explicito is not None:
            return explicito, False

        if _parece_consulta_transversal_eventos(pregunta.lower()):
            return None, False

        if self.id_evento_actual is not None:
            return self.id_evento_actual, True

        return None, False

    def registrar_turno(self, pregunta, respuesta, id_evento_usado):
        nuevo_id = _id_evento_a_recordar(respuesta, id_evento_usado)
        if nuevo_id is not None:
            self.id_evento_actual = nuevo_id
        self.historial.append({"pregunta": pregunta, "resumen": respuesta.get("resumen", "")})
        self.historial = self.historial[-MAX_TURNOS_HISTORIAL:]


def construir_payload(id_evento, historial, pregunta, origen="consola_local"):
    return {
        "id_evento": id_evento,
        "id_registro": None,
        "tipo_peticion": "chat_interactivo",
        "origen": origen,
        "usuario_solicitante": "raul",
        "rol_usuario": "organizador",
        "contexto": {"historial_conversacion": historial},
        "modo": "consulta",
        "datos": {"pregunta": pregunta},
    }


def _id_evento_parece_valido(id_evento, respuesta):
    if id_evento is None:
        return False
    bloqueos = " ".join(respuesta.get("bloqueos_detectados", []))
    if "no existe en los datos" in bloqueos:
        return False
    return True


def _id_evento_a_recordar(respuesta, id_evento_usado):
    """
    Decide que id_evento recordar para el siguiente turno, o None si no hay una señal clara
    (en ese caso se conserva lo que ya hubiera en memoria, no se borra).
    """
    if _id_evento_parece_valido(id_evento_usado, respuesta):
        return id_evento_usado

    eventos = (respuesta.get("datos_detectados") or {}).get("eventos")
    if isinstance(eventos, list) and len(eventos) == 1:
        return eventos[0].get("id_evento")

    return None


def fue_bloqueo_previo_a_id_evento(respuesta):
    """
    True si la respuesta se bloqueo en las comprobaciones de usuarios/escritura de
    src/nucleo.py, que se ejecutan ANTES de usar id_evento. Sirve para que la capa de chat
    (main.py, servidor.py) no diga "usando el evento X" cuando ese evento nunca llego a
    influir en la respuesta (seria confuso: el bloqueo no tiene nada que ver con el evento).
    """
    bloqueos = " ".join(respuesta.get("bloqueos_detectados", []))
    return "tabla usuarios" in bloqueos or "escritura" in bloqueos


def _extraer_id_evento_explicito(pregunta):
    """Busca un numero de evento explicito en la pregunta, p.ej. 'evento 12' o 'evento nº 12'."""
    m = re.search(r"evento\s*(?:n[uº°]?\s*)?(\d+)", pregunta.lower())
    return int(m.group(1)) if m else None
