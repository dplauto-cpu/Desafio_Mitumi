"""
funciones.py — motor de extracción por reglas (gratis, determinista,
sin llamadas externas). Alternativa: src.llm.extraer_briefing_llm(),
mismo esquema de salida, vía Groq — ver README.md.

El agente NO escribe en la BD, solo propone. La revisión humana es
obligatoria antes de guardar cualquier dato.
"""

import re
import os

from data.conocimiento.field_aliases_3 import FIELD_ALIASES
from data.conocimiento.cities_3 import CITIES
from data.conocimiento.event_types_3 import EVENT_TYPES
from data.conocimiento.status_3 import BUDGET_STATUS, EVENT_STATUS

from src.schemas import crear_estructura_vacia_completa, generar_aviso_y_validacion


# ---------------------------------------------------------------------
# 1. LECTURA DE ARCHIVOS (soporta .txt, .pdf, .docx)
# ---------------------------------------------------------------------
def leer_archivo(ruta_archivo):
    """
    Lee un archivo y devuelve su contenido como texto plano.

    Formatos soportados:
        - .txt  -> lectura directa
        - .pdf  -> usando PyPDF2 o pypdf
        - .docx -> usando python-docx

    Args:
        ruta_archivo (str): Ruta al archivo.

    Returns:
        str: Contenido del archivo como texto.

    Raises:
        ValueError: Si el formato no está soportado.
        Exception: Si hay un error al leer el archivo.
    """
    extension = os.path.splitext(ruta_archivo)[1].lower()

    if extension == ".txt":
        try:
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(ruta_archivo, "r", encoding="latin-1") as f:
                return f.read()

    elif extension == ".pdf":
        try:
            try:
                import PyPDF2
                lector = PyPDF2.PdfReader(ruta_archivo)
                texto = ""
                for pagina in lector.pages:
                    texto += pagina.extract_text() + "\n"
                return texto
            except ImportError:
                try:
                    import pypdf
                    lector = pypdf.PdfReader(ruta_archivo)
                    texto = ""
                    for pagina in lector.pages:
                        texto += pagina.extract_text() + "\n"
                    return texto
                except ImportError:
                    raise ImportError(
                        "No se encontró ninguna librería para leer PDF. "
                        "Instala PyPDF2 o pypdf: pip install PyPDF2"
                    )
        except Exception as e:
            raise Exception(f"Error al leer el PDF: {str(e)}")

    elif extension == ".docx":
        try:
            import docx
            documento = docx.Document(ruta_archivo)
            texto = ""
            for parrafo in documento.paragraphs:
                texto += parrafo.text + "\n"
            return texto
        except ImportError:
            raise ImportError(
                "No se encontró la librería para leer DOCX. "
                "Instala python-docx: pip install python-docx"
            )
        except Exception as e:
            raise Exception(f"Error al leer el DOCX: {str(e)}")

    else:
        raise ValueError(
            f"Lo siento, no soy capaz de leer este formato ({extension}). "
            "Solamente puedo leer .pdf, .docx y .txt"
        )


# ---------------------------------------------------------------------
# 2. EXTRACCIÓN POR ETIQUETA ("campo: valor")
# ---------------------------------------------------------------------
def buscar_por_etiquetas(texto):
    """
    Detecta líneas con el patrón "etiqueta: valor" y las relaciona con
    las claves internas de FIELD_ALIASES.

    Args:
        texto (str): Texto completo del briefing.

    Returns:
        dict: Claves internas de FIELD_ALIASES -> valor detectado
              (tal cual aparece en el texto, sin normalizar).
    """
    encontrados = {}
    lineas = texto.split("\n")

    for linea in lineas:
        linea_limpia = linea.lower().strip()

        if ":" not in linea_limpia:
            continue

        etiqueta = linea_limpia.split(":", 1)[0].strip()
        valor = linea.split(":", 1)[1].strip()

        if not valor:
            continue

        for campo, sinonimos in FIELD_ALIASES.items():
            if etiqueta in sinonimos:
                encontrados[campo] = valor

    return encontrados


def normalizar_estado_evento(valor):
    """
    Normaliza un valor de estado de evento etiquetado libremente al valor
    canónico de EVENT_STATUS (comparación insensible a mayúsculas). Si no
    coincide con ningún valor conocido, se devuelve tal cual — nunca se
    descarta ni se inventa un valor distinto al que puso la persona.

    Nota: solo se usa a partir de una etiqueta EXPLÍCITA del documento
    ("Estado del evento: Confirmado", "Descripción estado: ..."), nunca
    como heurístico de texto libre sobre todo el documento. Un heurístico
    de texto libre buscaría frases como "pendiente de aprobación" en
    cualquier parte del texto, y esa misma frase se usa también para el
    estado del PRESUPUESTO (ver detectar_estado_presupuesto) — así que
    contaminaría evento.estado con información que en realidad es de
    presupuesto.estado_presupuesto (ocurre literalmente en
    data/ejemplos/briefing_complejo.txt: "el estado del presupuesto
    sigue como pendiente de aprobación interna").

    Args:
        valor (str): Valor etiquetado tal cual aparece en el documento.

    Returns:
        str: Valor normalizado a EVENT_STATUS si hay coincidencia exacta
            (sin distinguir mayúsculas/minúsculas), o el valor original.
    """
    valor_limpio = valor.strip()
    valor_lower = valor_limpio.lower()
    for estado in EVENT_STATUS:
        if estado.lower() == valor_lower:
            return estado
    return valor_limpio


def normalizar_fecha_iso(valor):
    """
    Normaliza una fecha en formato DD/MM/AAAA o DD-MM-AAAA a ISO
    AAAA-MM-DD (el formato que usan tanto la BD como el contrato de
    API del proyecto). Si ya viene en ISO, o no se reconoce el
    formato, se devuelve tal cual.

    Args:
        valor (str): Fecha en cualquier formato de texto.

    Returns:
        str: Fecha en formato AAAA-MM-DD si fue posible normalizarla.
    """
    valor = valor.strip()

    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", valor):
        return valor

    resultado = re.match(r"^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$", valor)
    if resultado:
        dia, mes, anio = resultado.groups()
        return f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"

    return valor


# ---------------------------------------------------------------------
# 3. FUNCIONES DE EXTRACCIÓN POR TIPO DE DATO (texto libre)
# ---------------------------------------------------------------------
# Regla de oro del agente: NUNCA inventar ni deducir datos que no estén
# explícitos en el texto. Por eso los patrones "cajón de sastre" (que
# capturarían cualquier frase capitalizada como si fuera un nombre de
# evento o de empresa) se han retirado: es preferible dejar un campo
# vacío a rellenarlo con una suposición.
# ---------------------------------------------------------------------

def detectar_nombre_persona(texto):
    """Detecta nombres de persona en el texto ("Soy Laura Martínez", "Responsable: ...")."""
    patrones = [
        r"(?i:soy|me presento|mi nombre es)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)",
        r"(?i:responsable|contacto|persona de contacto)\s*[:;]\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)",
        r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)\s*(?:,|;|\-|\.)?\s*(?i:responsable|contacto|director|gerente)"
    ]
    for patron in patrones:
        resultado = re.search(patron, texto)
        if resultado:
            return resultado.group(1).strip()
    return ""


def detectar_empresa(texto):
    """Detecta el nombre de una empresa, anclado a palabra clave ("empresa X", "de la empresa X")."""
    patrones = [
        r"(?:empresa|compañía|organización)\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s\.]+?(?:S\.L\.|S\.A\.|SL|SA|SLL|S\.Coop\.|SCoop)?)(?=\s*(?:,|;|\.|\n|con sede|$))",
        r"de\s+la\s+empresa\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s\.]+?)(?=\s*(?:,|;|\.|\n|con sede|$))"
    ]
    for patron in patrones:
        resultado = re.search(patron, texto)
        if resultado:
            nombre = resultado.group(1).strip()
            if len(nombre) > 2:
                return nombre
    return ""


def detectar_email(texto):
    """Detecta direcciones de email en el texto."""
    patron = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    resultado = re.search(patron, texto)
    return resultado.group(0) if resultado else ""


def detectar_telefono(texto):
    """Detecta números de teléfono (+34 600 123 456 / 600 123 456 / 600123456)."""
    resultado = re.search(r'\+34[\s\-]?(\d{3}[\s\-]?\d{3}[\s\-]?\d{3})', texto)
    if resultado:
        telefono = re.sub(r'[\s\-]', '', resultado.group(1))
        if len(telefono) == 9:
            return f"+34{telefono}"

    for patron in (r'(\d{3}[\s\-]\d{3}[\s\-]\d{3})', r'(\d{9})'):
        resultado = re.search(patron, texto)
        if resultado:
            telefono = re.sub(r'[\s\-]', '', resultado.group(1))
            if len(telefono) == 9:
                return telefono

    return ""


def detectar_fechas(texto):
    """
    Detecta fechas en el texto y las devuelve en formato ISO AAAA-MM-DD
    (formato acordado en el contrato de API del proyecto y el que usan
    los CSV de la base de datos). Soporta rangos de N días ("15, 16 y 17
    de octubre de 2026", "15 al 17 de octubre de 2026"), fechas con
    separador ("15/10/2026") y fecha única.

    Returns:
        tuple: (fecha_inicio, fecha_fin) en formato AAAA-MM-DD.
    """
    meses = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "setiembre": "09", "octubre": "10",
        "noviembre": "11", "diciembre": "12"
    }

    patron_rango = r"((?:\d{1,2}\s*(?:,|y|al|a)?\s*)+)de\s*([a-záéíóúñ]+)\s*de\s*(\d{4})"
    resultado = re.search(patron_rango, texto.lower())
    if resultado:
        dias = re.findall(r"\d{1,2}", resultado.group(1))
        mes = meses.get(resultado.group(2), "")
        anio = resultado.group(3)
        if mes and dias:
            dia_inicio = dias[0].zfill(2)
            dia_fin = dias[-1].zfill(2)
            return f"{anio}-{mes}-{dia_inicio}", f"{anio}-{mes}-{dia_fin}"

    patron_separador = r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})"
    resultado = re.search(patron_separador, texto)
    if resultado:
        dia = resultado.group(1).zfill(2)
        mes = resultado.group(2).zfill(2)
        anio = resultado.group(3)
        return f"{anio}-{mes}-{dia}", f"{anio}-{mes}-{dia}"

    patron_simple = r"(\d{1,2})\s*de\s*([a-záéíóúñ]+)\s*de\s*(\d{4})"
    resultado = re.search(patron_simple, texto.lower())
    if resultado:
        dia = resultado.group(1).zfill(2)
        mes = meses.get(resultado.group(2), "")
        anio = resultado.group(3)
        if mes:
            fecha = f"{anio}-{mes}-{dia}"
            return fecha, fecha

    return "", ""


def detectar_ciudad(texto):
    """Detecta la ciudad en el texto usando la lista CITIES."""
    texto_lower = texto.lower()
    for ciudad in CITIES:
        if ciudad.lower() in texto_lower:
            return ciudad
    return ""


def detectar_tipo_evento(texto):
    """Detecta el tipo de evento usando la lista EVENT_TYPES."""
    texto_lower = texto.lower()
    for tipo in EVENT_TYPES:
        if tipo.lower() in texto_lower:
            return tipo
    return ""


def detectar_lugar(texto):
    """Detecta el lugar del evento (hotel, auditorio, etc.)."""
    patrones = [
        r"((?i:Hotel|Palacio|Auditorio|Museo|Centro|Sala|Teatro))\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+)*)",
        r"en\s+el\s+((?i:Hotel|Palacio|Auditorio|Museo|Centro|Sala|Teatro))\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+)*)",
        r"celebrará\s+en\s+el\s+((?i:Hotel|Palacio|Auditorio|Museo|Centro|Sala|Teatro))\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+)*)"
    ]
    for patron in patrones:
        resultado = re.search(patron, texto)
        if resultado:
            return (resultado.group(1) + " " + resultado.group(2)).strip()
    return ""


def detectar_numero_personas(texto):
    """Detecta el número de personas ("350 personas", "aforo de 350")."""
    patrones = [
        r"(\d+)\s*(?:personas|asistentes|invitados|participantes)",
        r"aforo\s*(?:de|)\s*(\d+)",
        r"para\s*(\d+)\s*personas"
    ]
    for patron in patrones:
        resultado = re.search(patron, texto, re.IGNORECASE)
        if resultado:
            return resultado.group(1)
    return ""


def detectar_presupuesto_maximo(texto):
    """Detecta el presupuesto máximo ("45.000 euros", "presupuesto de 45.000 €")."""
    patrones = [
        r"(\d+[\.\d]*)\s*(?:euros|€|eur)",
        r"presupuesto\s*(?:de|)\s*(\d+[\.\d]*)",
        r"(\d+[\.\d]*)\s*€"
    ]
    for patron in patrones:
        resultado = re.search(patron, texto, re.IGNORECASE)
        if resultado:
            numero = re.sub(r'\.', '', resultado.group(1))
            return numero
    return ""


def detectar_servicios(texto):
    """Detecta servicios (catering, audiovisuales...) y los devuelve como texto legible."""
    servicios_conocidos = [
        "catering", "audiovisuales", "streaming", "traducción", "traduccion",
        "sonido", "pantalla", "iluminación", "iluminacion", "seguridad",
        "parking", "wifi", "internet", "escenario", "montaje", "desmontaje"
    ]

    texto_lower = texto.lower()
    servicios_detectados = []

    for servicio in servicios_conocidos:
        if servicio in texto_lower:
            nombre = servicio.capitalize()
            if servicio == "traduccion":
                nombre = "Traducción"
            if servicio == "iluminacion":
                nombre = "Iluminación"
            servicios_detectados.append(nombre)

    if not servicios_detectados:
        return ""

    if len(servicios_detectados) == 1:
        return servicios_detectados[0]
    elif len(servicios_detectados) == 2:
        return f"{servicios_detectados[0]} y {servicios_detectados[1]}"
    else:
        ultimo = servicios_detectados[-1]
        primeros = ", ".join(servicios_detectados[:-1])
        return f"{primeros} y {ultimo}"


def detectar_estado_presupuesto(texto):
    """Detecta el estado del presupuesto usando la lista BUDGET_STATUS."""
    texto_lower = texto.lower()
    for estado in BUDGET_STATUS:
        if estado.lower() in texto_lower:
            return estado
    return ""


def _ponente_vacio():
    """Estructura vacía de un ponente individual (21 campos, ver schemas.py)."""
    return {
        "nombre_ponente": "",
        "doc_identificacion": "",
        "email": "",
        "sector": "",
        "telefono": "",
        "foto_link": "",
        "cv_link": "",
        "empresa": "",
        "cargo": "",
        "nombre_hotel": "",
        "nota_transporte": "",
        "horario_ida_transporte": "",
        "horario_vuelta_transporte": "",
        "localizacion_hotel": "",
        "horario_ponencia": "",
        "checking_horario": "",
        "ponente_estado": "",
        "presentacion_link": "",
        "billete_ida_link": "",
        "billete_vuelta_link": "",
        "tipo_ponencias": ""
    }


# Etiquetas reconocidas DENTRO de un bloque "Ponente N" ya delimitado. A
# diferencia de FIELD_ALIASES (data/conocimiento/field_aliases_3.py), aquí
# SÍ se pueden usar etiquetas genéricas ("nombre", "email", "empresa"...)
# sin ambigüedad, porque el bloque ya está acotado a un único ponente —
# no hay riesgo de contaminar el evento o el cliente con este dato.
_ALIAS_BLOQUE_PONENTE = {
    "nombre_ponente": ["nombre"],
    "doc_identificacion": ["dni", "nie", "documento", "documento identificación", "identificación"],
    "email": ["email", "correo", "mail"],
    "telefono": ["teléfono", "telefono", "móvil"],
    "empresa": ["empresa"],
    "cargo": ["cargo", "puesto", "rol", "posición"],
    "sector": ["sector", "área", "especialidad", "campo"],
}


def _extraer_ponente_de_bloque(bloque_texto):
    """
    Extrae los campos de UN ponente a partir del texto de su propio
    bloque "Ponente N" ya delimitado (ver detectar_ponentes). Reutiliza
    el mismo patrón "etiqueta: valor" línea a línea que
    buscar_por_etiquetas(), pero con un vocabulario de etiquetas propio
    (_ALIAS_BLOQUE_PONENTE) porque aquí sí es seguro usar etiquetas
    genéricas como "nombre" o "empresa" — el bloque ya pertenece a un
    solo ponente.

    LIMITACIÓN CONOCIDA: solo se detectan campos que vienen en su
    propia línea limpia "etiqueta: valor" (nombre, DNI, email,
    teléfono, empresa, cargo, sector, hotel). Campos que en el texto
    real aparecen mezclados en prosa libre dentro del mismo párrafo
    (horario de la ponencia, tipo de ponencia, nota de transporte,
    checkin...) no se intentan extraer de una frase libre — se dejan
    vacíos en vez de arriesgarse a inventar una interpretación
    (mismo principio de "no inventar" que en el resto del motor).

    Args:
        bloque_texto (str): Texto entre un encabezado "Ponente N" y el
            siguiente (o el final del documento).

    Returns:
        dict: Un ponente (ver _ponente_vacio para el esquema completo).
    """
    ponente = _ponente_vacio()

    for linea in bloque_texto.split("\n"):
        linea_limpia = linea.lower().strip()
        if ":" not in linea_limpia:
            continue

        etiqueta = linea_limpia.split(":", 1)[0].strip()
        valor = linea.split(":", 1)[1].strip()
        if not valor:
            continue

        for campo, sinonimos in _ALIAS_BLOQUE_PONENTE.items():
            if etiqueta in sinonimos:
                ponente[campo] = valor

    # "Hotel: NH Collection Bilbao. Necesita traslado..." -- el nombre
    # del hotel es solo el primer tramo, antes del punto; el resto de
    # la frase es prosa libre (nota de transporte) que no se parsea.
    resultado_hotel = re.search(r"(?im)^hotel\s*:\s*([^.\n]+)", bloque_texto)
    if resultado_hotel:
        ponente["nombre_hotel"] = resultado_hotel.group(1).strip()

    return ponente


def _extraer_ponente_de_parrafo(parrafo_texto):
    """
    Extrae los campos de UN ponente a partir de su propio párrafo de
    prosa libre, del formato "Ponente N: Nombre, cargo de la Empresa.
    Especialista en X. Correo: ..., teléfono .... Su ponencia será...
    Título: "...". Se alojará en el Hotel...". Es el formato real más
    habitual en los briefings de prueba (ver doc_prueba/) -- a
    diferencia de _extraer_ponente_de_bloque, aquí NO hay una línea
    propia por campo: todo está incrustado en un mismo párrafo, así
    que cada campo se busca con su propio patrón dentro del párrafo
    completo en vez de separar por líneas.

    Solo se extraen los campos con un patrón razonablemente fiable en
    prosa libre (nombre, email, teléfono, cargo+empresa, sector,
    título de la ponencia, hotel). El resto (horario de la ponencia,
    transporte, checkin, links...) se deja vacío: exigiría cruzar
    referencias relativas ("el día 5", "por la mañana") con las fechas
    del evento, con demasiado riesgo de construir un dato incorrecto
    -- mismo principio de "no inventar" que en el resto del motor.

    Args:
        parrafo_texto (str): Texto desde "Ponente N:" hasta el
            siguiente "Ponente N+1:" (o el final del documento).

    Returns:
        dict: Un ponente (ver _ponente_vacio para el esquema completo).
    """
    ponente = _ponente_vacio()

    resultado_nombre = re.match(r"(?im)^-?\s*ponente\s*\d+\s*:\s*([^,\n]+)", parrafo_texto)
    if resultado_nombre:
        ponente["nombre_ponente"] = resultado_nombre.group(1).strip()

    resultado_email = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', parrafo_texto)
    if resultado_email:
        ponente["email"] = resultado_email.group(0)

    # Tolera prefijos internacionales ("+49 30 9876543") además del
    # formato español -- a diferencia de detectar_telefono(), aquí el
    # teléfono va siempre anclado a la palabra "teléfono", así que se
    # puede ser más permisivo con el formato del número en sí.
    resultado_telefono = re.search(r"(?i)tel[ée]fono\s*:?\s*(\+?[\d][\d\s\-]{6,18}\d)", parrafo_texto)
    if resultado_telefono:
        ponente["telefono"] = resultado_telefono.group(1).strip()

    # "..., catedrático de la Universidad de Berlín." / "..., CEO de
    # GreenTech Ventures." -- cargo y empresa separados por el conector
    # "de"/"del"/"de la". LIMITACIÓN CONOCIDA: si el cargo mismo incluye
    # "de" (p. ej. "directora de Innovación en Tecnalia"), el reparto
    # entre cargo y empresa puede no ser exacto -- se prefiere un
    # reparto aproximado a dejarlo vacío, porque el texto igual queda
    # visible para que la persona lo corrija en la revisión.
    resultado_cargo_empresa = re.search(
        r",\s*([^,.]+?)\s+(?:de la|del|de)\s+([A-ZÁÉÍÓÚÑ][^.]+?)\.",
        parrafo_texto
    )
    if resultado_cargo_empresa:
        ponente["cargo"] = resultado_cargo_empresa.group(1).strip()
        ponente["empresa"] = resultado_cargo_empresa.group(2).strip()

    resultado_sector = re.search(
        r"(?i)(?:especialista|experto|experta)\s+en\s+([^.]+?)\.",
        parrafo_texto
    )
    if resultado_sector:
        ponente["sector"] = resultado_sector.group(1).strip()

    resultado_titulo = re.search(r'(?i)t[íi]tulo\s*:?\s*"([^"]+)"', parrafo_texto)
    if resultado_titulo:
        ponente["tipo_ponencias"] = resultado_titulo.group(1).strip()

    resultado_hotel = re.search(r"(?i)se alojará?\s+en\s+el\s+([^.\n]+?)\.", parrafo_texto)
    if resultado_hotel:
        ponente["nombre_hotel"] = resultado_hotel.group(1).strip()

    return ponente


def detectar_ponentes(texto):
    """
    Detecta múltiples ponentes en el texto. Soporta tres formatos, en
    este orden de prioridad:

    1. Párrafo de prosa libre por ponente ("Ponente 1: Nombre, cargo
       de la Empresa. Correo: ..., teléfono ...") -- el formato real
       más habitual (ver doc_prueba/ y _extraer_ponente_de_parrafo).
       "Ponente N:" es el inicio del párrafo, no una línea propia.
    2. Bloques numerados por ponente ("Ponente 1" sola en su línea,
       seguida de líneas propias "Nombre:", "DNI:", "Email:"...) --
       ver _extraer_ponente_de_bloque. Se prueba si no hay párrafos
       del formato 1 (el "Ponente N:" de ese formato lleva dos puntos
       en la misma línea; este no).
    3. Lista en una sola línea ("Los ponentes serán Ane Etxeberria y
       Jon Aguirre", "Ponentes: Ane Etxeberria, Jon Aguirre") -- solo
       se detecta el nombre; el resto de campos quedan vacíos. Se usa
       solo si no se encontró ninguno de los dos formatos anteriores.

    LIMITACIÓN CONOCIDA (formato de lista): si el documento etiqueta
    datos individuales de ponente (Email ponente:, Teléfono ponente:)
    y hay más de un ponente detectado por este formato, esos datos
    etiquetados solo se asignan al primer ponente (ver
    extraer_briefing) — a partir de una lista de nombres en texto
    libre no hay forma fiable de saber a cuál corresponde cada dato.

    Returns:
        list: Lista de diccionarios con la información de cada ponente.
    """
    partes = re.split(r"(?im)(?=^-?\s*ponente\s*\d+\s*:)", texto)
    parrafos_ponente = [p for p in partes if re.match(r"(?im)^-?\s*ponente\s*\d+\s*:", p)]
    if parrafos_ponente:
        return [_extraer_ponente_de_parrafo(p) for p in parrafos_ponente]

    bloques = re.split(r"(?im)^\s*ponente\s*\d+\s*$", texto)
    if len(bloques) > 1:
        return [_extraer_ponente_de_bloque(bloque) for bloque in bloques[1:]]

    ponentes = []

    patron_disparador = r"(?:ponentes|speakers|conferenciantes)\s*(?:serán|será|son|:)\s*(.+)"
    resultado = re.search(patron_disparador, texto, re.IGNORECASE)

    if resultado:
        resto_linea = resultado.group(1).split("\n")[0].split(".")[0]

        nombres = re.findall(
            r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+',
            resto_linea
        )

        for nombre in nombres:
            ponente = _ponente_vacio()
            ponente["nombre_ponente"] = nombre.strip()
            ponentes.append(ponente)

    return ponentes


def detectar_nombre_evento(texto):
    """
    Detecta el nombre del evento en el texto, anclado a una palabra
    clave ("Se trata del Congreso...", "Evento: ..."). No hay un patrón
    "cualquier línea capitalizada" de reserva: es preferible dejar el
    campo vacío a rellenarlo con una suposición.

    "organización(?:\\s+\\w+)?\\s+(?:de un|del|de nuestro|de nuestra)" permite
    como mucho UNA palabra entre "organización" y el conector (p. ej.
    "organización integral del Congreso...", ver
    data/ejemplos/briefing_complejo.txt) -- no un comodín sin límite,
    para no capturar frases que no tienen relación real con el nombre
    del evento. "de nuestro"/"de nuestra" cubre el fraseo real, muy
    habitual, de "para la organización de nuestro Congreso..." (ver
    doc_prueba/Sostenibilidad_complejo.docx y Global_elhorror.docx).

    El límite de la captura usa "\\n\\s*\\n" (línea en blanco, cambio
    de párrafo) y no un simple "\\n": un nombre de evento largo puede
    quedar partido en dos líneas físicas por el ancho del documento
    original (ver "III Congreso Internacional\\nde Movilidad
    Sostenible." en briefing_complejo.txt) -- un salto de línea suelto
    no es un límite real del nombre, solo el formato del documento.

    La coma como límite lleva un "(?!\\s*[A-ZÁÉÍÓÚÑ])": muchos nombres
    de evento reales enumeran varios temas dentro del propio nombre
    ("Congreso Mundial de Innovación, Tecnología y Sostenibilidad", ver
    doc_prueba/Global_elhorror.docx) -- si la coma cortase siempre, se
    perdería lo que viene después. Solo se trata como límite real si NO
    va seguida de una palabra en mayúscula (que indicaría que la
    enumeración del nombre continúa); si va seguida de minúscula
    ("Digital, que queremos celebrar...") sí es el final del nombre.
    """
    patrones = [
        r"(?i:se trata del|se trata de un|se celebra el|organización(?:\s+\w+)?\s+(?:de un|del|de nuestro|de nuestra))\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s,]+?)(?=\s*(?:,(?!\s*[A-ZÁÉÍÓÚÑ])|;|\.|\n\s*\n|con\s|para\s|en\s|del\s+\d|$))",
        r"(?i:evento|nombre del evento|título)\s*[:;]\s*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]+)"
    ]
    for patron in patrones:
        resultado = re.search(patron, texto)
        if resultado:
            # re.sub colapsa el salto de línea de un nombre partido en
            # dos líneas físicas (ver nota sobre "\n\s*\n" arriba) a un
            # espacio simple, para que el valor final sea una sola línea.
            nombre = re.sub(r"\s+", " ", resultado.group(1)).strip()
            if len(nombre) > 5:
                return nombre
    return ""


# ---------------------------------------------------------------------
# 4. FUNCIÓN PRINCIPAL: extraer_briefing
# ---------------------------------------------------------------------
def extraer_briefing(texto):
    """
    Extrae toda la información relevante de un briefing y la devuelve
    estructurada en un diccionario anidado, alineado con el esquema
    real de la base de datos.

    Motor de REGLAS (regex + etiquetas): gratis, determinista, sin
    llamadas externas. Alternativa: src.llm.extraer_briefing_llm(),
    mismo esquema de salida, vía Groq.

    Prioridad de las fuentes por campo: 1º etiqueta explícita en el
    documento ("Cliente: X"), 2º heurística de texto libre. Nunca se
    inventa un valor si ninguna de las dos lo encuentra.

    Args:
        texto (str): Texto completo del briefing.

    Returns:
        dict: Diccionario con la información extraída y validación.
    """
    etiquetas = buscar_por_etiquetas(texto)
    resultado = crear_estructura_vacia_completa()

    # --- 4.1 Evento (etiqueta explícita > heurística de texto libre) ---
    resultado["evento"]["nombre_evento"] = etiquetas.get("nombre_evento") or detectar_nombre_evento(texto)
    resultado["evento"]["ciudad"] = etiquetas.get("ciudad") or detectar_ciudad(texto)
    resultado["evento"]["lugar_confirmado"] = etiquetas.get("lugar_confirmado") or detectar_lugar(texto)
    resultado["evento"]["tipo_evento"] = etiquetas.get("tipo_evento") or detectar_tipo_evento(texto)
    resultado["evento"]["numero_personas"] = etiquetas.get("numero_personas") or detectar_numero_personas(texto)

    if "fecha_inicio" in etiquetas:
        resultado["evento"]["fecha_inicio"] = normalizar_fecha_iso(etiquetas["fecha_inicio"])
    if "fecha_fin" in etiquetas:
        resultado["evento"]["fecha_fin"] = normalizar_fecha_iso(etiquetas["fecha_fin"])
    if not resultado["evento"]["fecha_inicio"] or not resultado["evento"]["fecha_fin"]:
        fecha_inicio_detectada, fecha_fin_detectada = detectar_fechas(texto)
        resultado["evento"]["fecha_inicio"] = resultado["evento"]["fecha_inicio"] or fecha_inicio_detectada
        resultado["evento"]["fecha_fin"] = resultado["evento"]["fecha_fin"] or fecha_fin_detectada

    # --- 4.2 Cliente ---
    # Ponentes se detecta ANTES que Cliente (aunque en el esquema de
    # salida vaya después) porque email_reclamado_por_otro/
    # telefono_reclamado_por_otro necesitan conocer ya los emails y
    # teléfonos de los ponentes -- ver más abajo por qué.
    resultado["ponentes"] = detectar_ponentes(texto)

    resultado["cliente"]["cliente"] = etiquetas.get("cliente") or detectar_nombre_persona(texto)
    resultado["cliente"]["empresa"] = detectar_empresa(texto)

    emails_ponentes = {p["email"] for p in resultado["ponentes"] if p.get("email")}
    telefonos_ponentes = {p["telefono"] for p in resultado["ponentes"] if p.get("telefono")}

    # Dos formas de detectar que un email/teléfono "es de otro" (ponente
    # o espacio), no del cliente: 1) la etiqueta GLOBAL cualificada
    # ("Email ponente:") existe -- caso ya cubierto antes de tener
    # bloques de ponente; 2) el valor que se iba a asignar a cliente
    # coincide con el email/teléfono de un ponente ya detectado por
    # bloque (ver _extraer_ponente_de_bloque) -- necesario porque dentro
    # de un bloque "Ponente N" las etiquetas son genéricas ("Email:",
    # sin cualificar) y buscar_por_etiquetas(), que escanea el
    # documento entero sin distinguir bloques, las recoge igual bajo
    # "email_cliente"/"telefono_cliente" (se queda con la última línea
    # "Email:"/"Teléfono:" del documento, que puede ser la de un
    # ponente). Ver data/ejemplos/briefing_complejo.txt.
    email_reclamado_por_otro = (
        any(k in etiquetas for k in ("email_ponente", "email_contacto_espacio"))
        or etiquetas.get("email_cliente") in emails_ponentes
    )
    telefono_reclamado_por_otro = (
        any(k in etiquetas for k in ("telefono_ponente", "telefono_contacto_espacio"))
        or etiquetas.get("telefono_cliente") in telefonos_ponentes
    )

    # Importante: el chequeo "reclamado_por_otro" debe envolver TAMBIÉN
    # el valor de etiquetas.get(...), no solo el fallback de texto
    # libre -- si fuera "etiquetas.get(...) or (... reclamado_por_otro
    # ...)", el "or" cortocircuitaría antes de mirar
    # email_reclamado_por_otro en cuanto etiquetas.get() devolviera
    # algo, dejando pasar igualmente el email/teléfono de un ponente.
    resultado["cliente"]["email"] = (
        "" if email_reclamado_por_otro
        else (etiquetas.get("email_cliente") or detectar_email(texto))
    )
    resultado["cliente"]["telefono"] = (
        "" if telefono_reclamado_por_otro
        else (etiquetas.get("telefono_cliente") or detectar_telefono(texto))
    )
    resultado["cliente"]["sector"] = etiquetas.get("sector_cliente", "")

    if "ciudad_cliente" in etiquetas:
        resultado["cliente"]["ciudad"] = etiquetas["ciudad_cliente"]
    else:
        patron_sede = r"(?:sede|domicilio|con sede)\s+en\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)"
        sede = re.search(patron_sede, texto, re.IGNORECASE)
        if sede:
            resultado["cliente"]["ciudad"] = sede.group(1).strip()
        elif resultado["evento"]["ciudad"]:
            resultado["cliente"]["ciudad"] = resultado["evento"]["ciudad"]

    # --- 4.3 Espacio ---
    resultado["espacio"]["nombre_espacio"] = etiquetas.get("nombre_espacio") or detectar_lugar(texto)
    if resultado["espacio"]["nombre_espacio"] and not resultado["evento"]["lugar_confirmado"]:
        if "hotel" in resultado["espacio"]["nombre_espacio"].lower() or "palacio" in resultado["espacio"]["nombre_espacio"].lower():
            resultado["evento"]["lugar_confirmado"] = resultado["espacio"]["nombre_espacio"]

    resultado["espacio"]["direccion"] = etiquetas.get("direccion_espacio", "")
    resultado["espacio"]["capacidad_total"] = etiquetas.get("capacidad_total", "")
    resultado["espacio"]["aforo"] = etiquetas.get("aforo_espacio", "")
    resultado["espacio"]["telefono_contacto"] = etiquetas.get("telefono_contacto_espacio", "")
    resultado["espacio"]["nombre_contacto"] = etiquetas.get("nombre_contacto_espacio", "")
    resultado["espacio"]["email_contacto"] = etiquetas.get("email_contacto_espacio", "")

    if resultado["evento"]["ciudad"]:
        resultado["espacio"]["ciudad"] = resultado["evento"]["ciudad"]

    # --- 4.4 Sala ---
    resultado["sala"]["nombre_sala"] = etiquetas.get("nombre_sala", "")
    resultado["sala"]["tipo"] = etiquetas.get("tipo_sala", "")
    resultado["sala"]["nota_sala"] = etiquetas.get("nota_sala", "")
    resultado["sala"]["capacidad_max_sala"] = (
        etiquetas.get("capacidad_max_sala")
        or resultado["evento"]["numero_personas"]
    )

    # --- 4.5 Ponentes ---
    # (resultado["ponentes"] ya se calculó antes de "4.2 Cliente" -- ver
    # comentario ahí)

    if len(resultado["ponentes"]) == 1:
        # ".get(x) or etiquetas.get(y)" y no una asignación directa:
        # si este único ponente vino de un bloque "Ponente 1" ya
        # parseado (ver _extraer_ponente_de_bloque), sus campos
        # detectados ahí NO deben sobrescribirse con "" solo porque el
        # documento no usa además las etiquetas GLOBALES cualificadas
        # ("Email ponente:", "Empresa del ponente:"...). Si en cambio
        # vino del formato de lista de un solo nombre (sin bloque),
        # ponente.get(x) es siempre "" y el resultado es idéntico al
        # comportamiento anterior.
        ponente = resultado["ponentes"][0]
        ponente["doc_identificacion"] = ponente.get("doc_identificacion") or etiquetas.get("docu_identificacion", "")
        ponente["email"] = ponente.get("email") or etiquetas.get("email_ponente", "")
        ponente["sector"] = ponente.get("sector") or etiquetas.get("sector_ponente", "")
        ponente["telefono"] = ponente.get("telefono") or etiquetas.get("telefono_ponente", "")
        ponente["foto_link"] = ponente.get("foto_link") or etiquetas.get("foto_link", "")
        ponente["cv_link"] = ponente.get("cv_link") or etiquetas.get("cv_link", "")
        ponente["empresa"] = ponente.get("empresa") or etiquetas.get("empresa_ponente", "")
        ponente["cargo"] = ponente.get("cargo") or etiquetas.get("cargo_ponente", "")
        ponente["nombre_hotel"] = ponente.get("nombre_hotel") or etiquetas.get("nombre_hotel", "")
        ponente["nota_transporte"] = ponente.get("nota_transporte") or etiquetas.get("nota_transporte", "")
        ponente["horario_ida_transporte"] = ponente.get("horario_ida_transporte") or etiquetas.get("horario_ida_transporte", "")
        ponente["horario_vuelta_transporte"] = ponente.get("horario_vuelta_transporte") or etiquetas.get("horario_vuelta_transporte", "")
        ponente["localizacion_hotel"] = ponente.get("localizacion_hotel") or etiquetas.get("localizacion_hotel", "")
        ponente["horario_ponencia"] = ponente.get("horario_ponencia") or etiquetas.get("horario_ponencia", "")
        ponente["checking_horario"] = ponente.get("checking_horario") or etiquetas.get("checkin_horario", "")
        ponente["ponente_estado"] = ponente.get("ponente_estado") or etiquetas.get("ponente_estado", "")
        ponente["presentacion_link"] = ponente.get("presentacion_link") or etiquetas.get("presentacion_link", "")
        ponente["billete_ida_link"] = ponente.get("billete_ida_link") or etiquetas.get("billete_ida_link", "")
        ponente["billete_vuelta_link"] = ponente.get("billete_vuelta_link") or etiquetas.get("billete_vuelta_link", "")
        ponente["tipo_ponencias"] = ponente.get("tipo_ponencias") or etiquetas.get("tipo_ponencia", "")

    # --- 4.6 Presupuesto ---
    resultado["presupuesto"]["estado_presupuesto"] = etiquetas.get("estado_presupuesto") or detectar_estado_presupuesto(texto)
    resultado["presupuesto"]["total"] = etiquetas.get("total") or detectar_presupuesto_maximo(texto)
    if "fecha_presupuesto" in etiquetas:
        resultado["presupuesto"]["fecha"] = normalizar_fecha_iso(etiquetas["fecha_presupuesto"])
    resultado["presupuesto"]["nota_ubicacion"] = etiquetas.get("nota_ubicacion", "")
    resultado["presupuesto"]["precio_ubicacion"] = etiquetas.get("precio_ubicacion", "")
    resultado["presupuesto"]["precio_catering"] = etiquetas.get("precio_catering", "")
    resultado["presupuesto"]["precio_audiovisuales"] = etiquetas.get("precio_audiovisuales", "")
    resultado["presupuesto"]["precio_otros"] = etiquetas.get("precio_otros", "")
    resultado["presupuesto"]["nota_catering"] = etiquetas.get("nota_catering", "")
    resultado["presupuesto"]["nota_audiovisuales"] = etiquetas.get("nota_audiovisuales", "")
    resultado["presupuesto"]["nota_otros"] = etiquetas.get("nota_otros", "")

    servicios = detectar_servicios(texto)
    observaciones = etiquetas.get("observaciones", "")
    if servicios:
        nota_servicios = f"Servicios solicitados: {servicios}"
        observaciones = f"{observaciones} | {nota_servicios}" if observaciones else nota_servicios
    resultado["presupuesto"]["observaciones"] = observaciones

    # --- 4.7 Estado y nota del evento ---
    if "descripcion_estado" in etiquetas:
        resultado["evento"]["estado"] = normalizar_estado_evento(etiquetas["descripcion_estado"])

    resultado["evento"]["nota"] = etiquetas.get("nota", "")

    return generar_aviso_y_validacion(resultado)


def procesar_archivo(ruta_archivo):
    """
    Lee un archivo y extrae la información del briefing en un solo paso.
    Útil para pruebas rápidas.

    Args:
        ruta_archivo (str): Ruta al archivo.

    Returns:
        dict: Diccionario con la información extraída.
    """
    try:
        texto = leer_archivo(ruta_archivo)
        return extraer_briefing(texto)
    except Exception as e:
        return {
            "error": True,
            "mensaje": str(e),
            "_validacion": {
                "campos_detectados": [],
                "campos_pendientes": ["error_lectura"],
                "porcentaje_completado": 0
            }
        }
