
from field_aliases_3 import FIELD_ALIASES
from cities_3 import CITIES
from event_types_3 import EVENT_TYPES
from status_3 import BUDGET_STATUS

import re

def formatear_fecha(fecha):
    if "-" in fecha:
        partes = fecha.split("-")

        if len(partes) == 3:
            anio = partes[0]
            mes = partes[1]
            dia = partes[2]

            return f"{dia}/{mes}/{anio}"

    return fecha


def crear_estructura_vacia():
    return {
        "nombre_evento": "",
        "cliente": "",
        "tipo_evento": "",
        "numero_personas": "",
        "fecha_inicio": "",
        "fecha_fin": "",
        "ciudad": "",
        "estado_presupuesto": ""
    }


def buscar_por_etiqueta(texto, datos):
    lineas = texto.split("\n")

    for linea in lineas:
        linea_limpia = linea.lower().strip()

        if ":" not in linea_limpia:
            continue

        etiqueta = linea_limpia.split(":", 1)[0].strip()
        valor = linea.split(":", 1)[1].strip()

        for campo, sinonimos in FIELD_ALIASES.items():
            if etiqueta in sinonimos:
                #datos[campo] = valor
                if campo in ["fecha_inicio", "fecha_fin"]:
                    datos[campo] = formatear_fecha(valor)
                else:
                    datos[campo] = valor

    return datos


def buscar_por_patrones(texto, datos):
    texto_lower = texto.lower()

    # Detectar nombre del evento: "llamada Congreso de Innovación"
    if datos["nombre_evento"] == "":
        patron_nombre = r"(?:llamada|llamado|titulado|titulada)\s+(.+?)(?=\s+para\s+nuestro cliente|\s+para\s+cliente|\s+en\s+|\.|\n|$)"
        resultado = re.search(patron_nombre, texto, re.IGNORECASE)

        if resultado:
            datos["nombre_evento"] = resultado.group(1).strip()



    # Cliente: detecta "cliente Michelin"
    if datos["cliente"] == "":
        patron_cliente = r"cliente\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ0-9\-&\. ]+?)(?=\s+en\s+|\s+para\s+\d+|\.|\n|$)"
        resultado = re.search(patron_cliente, texto)

        if resultado:
            datos["cliente"] = resultado.group(1).strip()

    # Número de personas: detecta "250 personas"
    if datos["numero_personas"] == "":
        patron_personas = r"(\d+)\s*(personas|asistentes|invitados|participantes)"
        resultado = re.search(patron_personas, texto_lower)

        if resultado:
            datos["numero_personas"] = resultado.group(1)

    return datos





#def buscar_por_patrones(texto, datos):
#    texto_lower = texto.lower()

#    if datos["cliente"] == "":
#        if "cliente " in texto_lower:
#            inicio = texto_lower.find("cliente ")
#            nombre = texto[inicio + len("cliente "):]
#
#            nombre = nombre.split(".")[0]
#            nombre = nombre.split("\n")[0]
#
#            datos["cliente"] = nombre.strip()

#    return datos

def validar_datos(datos):
    campos_obligatorios = [
        "nombre_evento",
        "cliente",
        "tipo_evento",
        "numero_personas",
        "fecha_inicio",
        "fecha_fin",
        "ciudad"
    ]

    campos_detectados = []
    campos_pendientes = []

    for campo in campos_obligatorios:
        if datos.get(campo):
            campos_detectados.append(campo)
        else:
            campos_pendientes.append(campo)

    datos["_validacion"] = {
        "campos_detectados": campos_detectados,
        "campos_pendientes": campos_pendientes,
        "porcentaje_completado": round(
            len(campos_detectados) / len(campos_obligatorios) * 100
        )
    }

    return datos




def extraer_briefing(texto):
    datos = crear_estructura_vacia()

    datos = buscar_por_etiqueta(texto, datos)
    datos = buscar_por_patrones(texto, datos)
    datos = buscar_entidades(texto, datos)
    datos = buscar_fechas(texto, datos)
    datos = validar_datos(datos)

    return datos


def buscar_entidades(texto, datos):
    texto_lower = texto.lower()

    if datos["ciudad"] == "":
        for ciudad in CITIES:
            if ciudad.lower() in texto_lower:
                datos["ciudad"] = ciudad
                break

    if datos["tipo_evento"] == "":
        for tipo in EVENT_TYPES:
            if tipo.lower() in texto_lower:
                datos["tipo_evento"] = tipo
                break

    if datos["estado_presupuesto"] == "":
        for estado in BUDGET_STATUS:
            if estado.lower() in texto_lower:
                datos["estado_presupuesto"] = estado
                break

    return datos


def buscar_fechas(texto, datos):
    texto_lower = texto.lower()

    meses = {
        "enero": "01",
        "febrero": "02",
        "marzo": "03",
        "abril": "04",
        "mayo": "05",
        "junio": "06",
        "julio": "07",
        "agosto": "08",
        "septiembre": "09",
        "setiembre": "09",
        "octubre": "10",
        "noviembre": "11",
        "diciembre": "12"
    }

    patron_rango = r"(\d{1,2})\s*(?:y|al|-)\s*(\d{1,2})\s*de\s*([a-záéíóúñ]+)\s*de\s*(\d{4})"
    resultado = re.search(patron_rango, texto_lower)

    if resultado:
        dia_inicio = resultado.group(1).zfill(2)
        dia_fin = resultado.group(2).zfill(2)
        mes = meses.get(resultado.group(3), "")
        anio = resultado.group(4)

        if mes:

        # fecha de la forma 2026-2-15 (año-mes-dia)
        #    datos["fecha_inicio"] = f"{anio}-{mes}-{dia_inicio}"
        #    datos["fecha_fin"] = f"{anio}-{mes}-{dia_fin}"

        # fecha de la forma 15-2-2026 (dia-mes-año)
            datos["fecha_inicio"] = f"{dia_inicio}/{mes}/{anio}"
            datos["fecha_fin"] = f"{dia_fin}/{mes}/{anio}"


    return datos