"""Construye y envía el email diario de resumen (ver sección 10 del build brief)."""

# traigo logging para dejar mensajes en el registro cuando algo falla
import logging
# traigo smtplib para poder enviar correos por SMTP
import smtplib
# traigo MIMEText para construir el cuerpo del email como texto
from email.mime.text import MIMEText

# traigo del config los datos del correo y la lista de destinatarios
from vigil.config import DESTINATARIOS, EMAIL_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
# traigo los moldes para tipar bien las convocatorias y sus veredictos
from vigil.schemas import Convocatoria, VeredictoRelevancia

# creo un registrador con el nombre de este módulo
logger = logging.getLogger(__name__)

# defino un atajo de tipo: cada relevante es una convocatoria con su veredicto
Relevante = tuple[Convocatoria, VeredictoRelevancia]


# doy formato de texto a una sola convocatoria para el email
def _formatear_convocatoria(convocatoria: Convocatoria, veredicto: VeredictoRelevancia) -> str:
    # preparo las líneas de esta convocatoria una a una
    lineas = [
        # pongo el objeto del contrato como titular con un asterisco
        f"* {convocatoria.objeto}",
        # añado quién convoca
        f"  Organo convocante: {convocatoria.organo_convocante}",
        # añado el importe, o un aviso si no lo pude sacar
        f"  Importe: {convocatoria.importe or 'No se pudo extraer del pliego'}",
        # añado el plazo, o un aviso si no lo pude sacar
        f"  Plazo de presentacion: {convocatoria.plazo_presentacion or 'No se pudo extraer del pliego'}",
        # añado el enlace al pliego
        f"  Enlace al pliego: {convocatoria.enlace_pliego}",
        # añado la explicación de por qué encaja con Mitumi
        f"  Por que encaja: {veredicto.motivo}",
    ]
    # si hay requisitos que no pude verificar, los aviso también
    if veredicto.campos_no_verificables:
        # añado una línea listando esos requisitos sin verificar
        lineas.append(
            "  Sin verificar contra el perfil de Mitumi: "
            + ", ".join(veredicto.campos_no_verificables)
        )
    # uno todas las líneas con saltos de línea y las devuelvo
    return "\n".join(lineas)


# construyo el asunto y el cuerpo completos del email
def construir_email(relevantes: list[Relevante]) -> tuple[str, str]:
    # cuento cuántas convocatorias relevantes hay
    n = len(relevantes)
    # elijo singular o plural según el número
    concurso = "concurso relevante" if n == 1 else "concursos relevantes"
    # armo el asunto con el número y las tres diputaciones
    asunto = f"Vigil — {n} {concurso} hoy (Araba/Gipuzkoa/Bizkaia)"
    # armo el cuerpo juntando cada convocatoria formateada, separadas por líneas en blanco
    cuerpo = "\n\n".join(_formatear_convocatoria(conv, ver) for conv, ver in relevantes)
    # devuelvo el asunto y el cuerpo
    return asunto, cuerpo


# envío el email de resumen
def enviar_email(relevantes: list[Relevante]) -> bool:
    """Envía el email de resumen.

    Devuelve True si se envió correctamente, False si falló (el error queda
    logueado). No hay reintento automático — no hace falta para el MVP (ver
    sección 9 del build brief).
    """
    # si no hay nada relevante, no envío nada y aviso con False
    if not relevantes:
        return False

    # construyo el asunto y el cuerpo del email
    asunto, cuerpo = construir_email(relevantes)
    # meto el cuerpo en un mensaje de texto plano con codificación utf-8
    mensaje = MIMEText(cuerpo, "plain", "utf-8")
    # pongo el asunto del mensaje
    mensaje["Subject"] = asunto
    # pongo quién lo envía
    mensaje["From"] = EMAIL_FROM
    # pongo los destinatarios separados por comas
    mensaje["To"] = ", ".join(DESTINATARIOS)

    # intento enviar el correo y capturo cualquier fallo
    try:
        # abro la conexión con el servidor de correo y la cierro sola al salir
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as servidor:
            # activo el cifrado de la conexión
            servidor.starttls()
            # me identifico con usuario y contraseña
            servidor.login(SMTP_USER, SMTP_PASSWORD)
            # envío el mensaje a todos los destinatarios
            servidor.sendmail(EMAIL_FROM, DESTINATARIOS, mensaje.as_string())
        # si llegué hasta aquí, todo fue bien
        return True
    # si algo falló en el envío...
    except Exception:
        # apunto el error completo en el registro
        logger.exception("Fallo al enviar el email de resumen de Vigil.")
        # aviso de que no se pudo enviar
        return False
