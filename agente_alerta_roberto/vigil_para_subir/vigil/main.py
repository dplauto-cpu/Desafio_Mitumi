"""Entry point de Vigil: orquesta el flujo end-to-end (ver sección 8 del build brief)."""

# traigo logging para ir dejando mensajes de lo que va pasando
import logging

# traigo los módulos de deduplicado y de envío de email
from vigil import dedupe, notifier
# traigo la ruta del fichero de base de datos
from vigil.config import SQLITE_PATH
# traigo la función que estructura cada convocatoria con el LLM
from vigil.extractor import extraer_convocatoria
# traigo la función que decide si una convocatoria es relevante
from vigil.relevance import evaluar_relevancia
# traigo los moldes para tipar convocatorias y veredictos
from vigil.schemas import Convocatoria, VeredictoRelevancia
# traigo la función que lee la web y devuelve las convocatorias crudas
from vigil.sources import obtener_convocatorias

# configuro el registro para que muestre fecha, nivel y mensaje
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
# creo mi registrador con un nombre claro
logger = logging.getLogger("vigil.main")


# esta es la función principal que ejecuta todo el proceso
def run() -> None:
    # intento leer las convocatorias de la web
    try:
        # llamo al scraper y guardo las convocatorias crudas
        crudas = obtener_convocatorias()
    # si falla la lectura de la web...
    except Exception:
        # apunto el error y termino sin enviar nada (no hay datos que reportar)
        logger.exception("Fallo al leer KontratazioA — se aborta sin enviar email.")
        return

    # dejo constancia de cuántas convocatorias he encontrado
    logger.info("Encontradas %d convocatorias en las tres diputaciones.", len(crudas))

    # preparo una lista vacía donde iré metiendo las que sean relevantes
    relevantes: list[tuple[Convocatoria, VeredictoRelevancia]] = []

    # abro la base de datos para consultar y guardar lo ya procesado
    with dedupe.get_connection(SQLITE_PATH) as conn:
        # recorro una a una todas las convocatorias crudas
        for cruda in crudas:
            # saco el id de expediente de la convocatoria
            id_expediente = cruda.get("id_expediente")
            # saco el enlace al pliego (o cadena vacía si no hay)
            url = cruda.get("enlace_pliego") or ""

            # si la convocatoria no tiene id, no puedo deduplicarla: la salto
            if not id_expediente:
                # aviso en el registro de que la ignoro
                logger.warning(
                    "Convocatoria sin id_expediente, se ignora: %s", cruda.get("objeto")
                )
                # paso a la siguiente
                continue

            # si ya la procesé en un día anterior, la salto
            if dedupe.ya_procesado(conn, id_expediente):
                continue

            # intento estructurar la convocatoria con el LLM
            try:
                # convierto la convocatoria cruda en un objeto limpio
                convocatoria = extraer_convocatoria(cruda)
            # si falla la extracción...
            except Exception:
                # apunto el error y NO la marco como procesada, para reintentar mañana
                logger.exception(
                    "Fallo al extraer la convocatoria %s — no se marca como procesada, "
                    "se reintentará mañana.",
                    id_expediente,
                )
                # paso a la siguiente
                continue

            # intento evaluar si la convocatoria es relevante
            try:
                # pido el veredicto de relevancia al LLM
                veredicto = evaluar_relevancia(convocatoria)
            # si falla la evaluación...
            except Exception:
                # apunto el error y NO la marco como procesada, para reintentar mañana
                logger.exception(
                    "Fallo al evaluar relevancia de %s — no se marca como procesada, "
                    "se reintentará mañana.",
                    id_expediente,
                )
                # paso a la siguiente
                continue

            # llegué hasta aquí sin fallos, así que la marco como procesada
            dedupe.marcar_procesado(conn, id_expediente, url)

            # si el veredicto dice que es relevante...
            if veredicto.relevante:
                # la añado a la lista de relevantes con su veredicto
                relevantes.append((convocatoria, veredicto))
                # dejo constancia de que es relevante y por qué
                logger.info("Relevante: %s — %s", id_expediente, veredicto.motivo)
            # si no es relevante...
            else:
                # dejo constancia de que no lo es y por qué
                logger.info("No relevante: %s — %s", id_expediente, veredicto.motivo)

    # si al final hay alguna convocatoria relevante...
    if relevantes:
        # intento enviar el email de resumen
        if notifier.enviar_email(relevantes):
            # si se envió bien, lo apunto
            logger.info("Email enviado con %d convocatorias relevantes.", len(relevantes))
        # si no se pudo enviar...
        else:
            # apunto el error (el detalle ya quedó en el log anterior)
            logger.error("No se pudo enviar el email (ver log anterior).")
    # si no hay nada relevante...
    else:
        # lo apunto y no envío ningún email
        logger.info("No hay convocatorias relevantes hoy — no se envía email.")


# si ejecuto este fichero directamente, arranco el proceso
if __name__ == "__main__":
    run()
