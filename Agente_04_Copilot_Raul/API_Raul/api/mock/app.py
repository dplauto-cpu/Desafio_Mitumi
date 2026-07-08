"""
app.py — API de gestión de eventos y ponentes (Flask).

Implementa los endpoints del contrato "idioma común".
Funciona sobre datos de prueba en memoria (datos.py), así que arranca
sin necesitar PostgreSQL. Cuando la BD real esté lista, se cambia datos.py
y estos endpoints siguen igual.

Arrancar:   python app.py
Probar:     http://localhost:5000/eventos
"""

from flask import Flask, request, jsonify
from functools import wraps
import datos

app = Flask(__name__)

# CORS: permite que el frontend (otra dirección/puerto) llame a esta API
# desde el navegador. Sin esto, el navegador bloquea las peticiones.
try:
    from flask_cors import CORS
    CORS(app)
except ImportError:
    print("Aviso: flask-cors no instalado. El front en navegador puede fallar por CORS.")


# ===========================================================================
# Utilidades comunes
# ===========================================================================

def error(codigo, mensaje, http=400, detalles=None):
    """Devuelve una respuesta de error con el formato único del contrato."""
    cuerpo = {"error": True, "codigo": codigo, "mensaje": mensaje}
    if detalles is not None:
        cuerpo["detalles"] = detalles
    return jsonify(cuerpo), http


def paginar(lista):
    """Aplica paginación y devuelve la lista envuelta con metadatos."""
    try:
        pagina = int(request.args.get("pagina", 1))
        por_pagina = int(request.args.get("por_pagina", 20))
    except ValueError:
        pagina, por_pagina = 1, 20

    total = len(lista)
    inicio = (pagina - 1) * por_pagina
    fin = inicio + por_pagina
    return {
        "datos": lista[inicio:fin],
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total": total,
    }


def requiere_campos(cuerpo, campos):
    """Devuelve el nombre del primer campo obligatorio que falte, o None."""
    if cuerpo is None:
        return campos[0] if campos else None
    for c in campos:
        if c not in cuerpo or cuerpo[c] in (None, ""):
            return c
    return None


# ---- Autenticación sencilla (suficiente para la demo) ----------------------
# Guardamos tokens en memoria: token -> usuario.
_sesiones = {}


def token_de(usuario):
    tok = f"token-{usuario['id']}"
    _sesiones[tok] = usuario
    return tok


def usuario_actual():
    """Lee el token de la cabecera Authorization y devuelve el usuario o None."""
    cabecera = request.headers.get("Authorization", "")
    if cabecera.startswith("Bearer "):
        return _sesiones.get(cabecera[7:])
    return None


def requiere_login(rol=None):
    """Decorador: exige sesión, y opcionalmente un rol concreto."""
    def decorador(f):
        @wraps(f)
        def envoltorio(*args, **kwargs):
            u = usuario_actual()
            if u is None:
                return error("NO_AUTENTICADO", "Necesitas iniciar sesión.", 401)
            if rol and u.get("rol") != rol:
                return error("SIN_PERMISO", "No tienes permiso para esto.", 403)
            return f(*args, **kwargs)
        return envoltorio
    return decorador


# ===========================================================================
# 2. Autenticación
# ===========================================================================

@app.post("/auth/login")
def login():
    cuerpo = request.get_json(silent=True) or {}
    falta = requiere_campos(cuerpo, ["email", "password"])
    if falta:
        return error("CAMPO_OBLIGATORIO", f"El campo '{falta}' es obligatorio.",
                     400, {"campo": falta})

    for u in datos.listar("usuarios"):
        if u["email"] == cuerpo["email"] and u["password"] == cuerpo["password"]:
            publico = {"id": u["id"], "nombre": u["nombre"], "rol": u["rol"]}
            return jsonify({"token": token_de(u), "usuario": publico})
    return error("CREDENCIALES_INVALIDAS", "Email o contraseña incorrectos.", 401)


@app.post("/auth/logout")
def logout():
    cabecera = request.headers.get("Authorization", "")
    if cabecera.startswith("Bearer "):
        _sesiones.pop(cabecera[7:], None)
    return jsonify({"ok": True})


@app.get("/auth/yo")
@requiere_login()
def yo():
    u = usuario_actual()
    return jsonify({"id": u["id"], "nombre": u["nombre"], "rol": u["rol"]})


# ===========================================================================
# 3. Eventos
# ===========================================================================

@app.get("/eventos")
def listar_eventos():
    eventos = datos.listar("eventos")
    # filtro opcional por estado
    estado = request.args.get("estado")
    if estado:
        eventos = [e for e in eventos if e["estado"] == estado]
    # búsqueda opcional por nombre
    buscar = request.args.get("buscar")
    if buscar:
        eventos = [e for e in eventos if buscar.lower() in e["nombre"].lower()]
    return jsonify(paginar(eventos))


@app.get("/eventos/<int:id_>")
def detalle_evento(id_):
    evento = datos.obtener("eventos", id_)
    if evento is None:
        return error("NO_ENCONTRADO", "Evento no encontrado.", 404)
    return jsonify(evento)


@app.post("/eventos")
def crear_evento():
    cuerpo = request.get_json(silent=True) or {}
    falta = requiere_campos(cuerpo, ["nombre", "cliente"])
    if falta:
        return error("CAMPO_OBLIGATORIO", f"El campo '{falta}' es obligatorio.",
                     400, {"campo": falta})

    from datetime import datetime
    nuevo = {
        "nombre": cuerpo["nombre"],
        "cliente": cuerpo["cliente"],
        "tipo": cuerpo.get("tipo"),
        "num_personas": cuerpo.get("num_personas"),
        "fecha_inicio": cuerpo.get("fecha_inicio"),
        "fecha_fin": cuerpo.get("fecha_fin"),
        "estado": cuerpo.get("estado", "borrador"),
        "lugar_id": cuerpo.get("lugar_id"),
        "creado_en": datetime.now().isoformat(timespec="seconds"),
    }
    creado = datos.crear("eventos", nuevo)
    return jsonify(creado), 201


@app.put("/eventos/<int:id_>")
def editar_evento(id_):
    cuerpo = request.get_json(silent=True) or {}
    actualizado = datos.actualizar("eventos", id_, cuerpo)
    if actualizado is None:
        return error("NO_ENCONTRADO", "Evento no encontrado.", 404)
    return jsonify(actualizado)


@app.delete("/eventos/<int:id_>")
def borrar_evento(id_):
    if datos.borrar("eventos", id_):
        return jsonify({"ok": True, "mensaje": "Evento eliminado."})
    return error("NO_ENCONTRADO", "Evento no encontrado.", 404)


# ===========================================================================
# 4. Lugar
# ===========================================================================

@app.get("/lugares")
def listar_lugares():
    lugares = datos.listar("lugares")
    buscar = request.args.get("buscar")
    if buscar:
        lugares = [l for l in lugares
                   if buscar.lower() in l["nombre"].lower()
                   or buscar.lower() in l["zona"].lower()]
    return jsonify(paginar(lugares))


@app.get("/lugares/<int:id_>")
def detalle_lugar(id_):
    lugar = datos.obtener("lugares", id_)
    if lugar is None:
        return error("NO_ENCONTRADO", "Lugar no encontrado.", 404)
    return jsonify(lugar)


@app.post("/eventos/<int:id_>/lugar")
def asignar_lugar(id_):
    if datos.obtener("eventos", id_) is None:
        return error("NO_ENCONTRADO", "Evento no encontrado.", 404)
    cuerpo = request.get_json(silent=True) or {}
    falta = requiere_campos(cuerpo, ["lugar_id"])
    if falta:
        return error("CAMPO_OBLIGATORIO", f"El campo '{falta}' es obligatorio.",
                     400, {"campo": falta})

    asignacion = {
        "evento_id": id_,
        "lugar_id": cuerpo["lugar_id"],
        "fecha_inicio": cuerpo.get("fecha_inicio"),
        "fecha_fin": cuerpo.get("fecha_fin"),
        "presupuesto": cuerpo.get("presupuesto"),
        "estado": cuerpo.get("estado", "propuesto"),
        "servicios_incluidos": cuerpo.get("servicios_incluidos", []),
    }
    creado = datos.crear("lugares_asignados", asignacion)
    # reflejar el lugar en el evento
    datos.actualizar("eventos", id_, {"lugar_id": cuerpo["lugar_id"]})
    return jsonify(creado), 201


@app.post("/lugares/<int:id_>/contactar")
def contactar_lugar(id_):
    if datos.obtener("lugares", id_) is None:
        return error("NO_ENCONTRADO", "Lugar no encontrado.", 404)
    cuerpo = request.get_json(silent=True) or {}
    solicitud = {
        "lugar_id": id_,
        "fecha": cuerpo.get("fecha"),
        "mensaje": cuerpo.get("mensaje", "Solicitud de disponibilidad."),
        "estado": "enviada",
    }
    creado = datos.crear("solicitudes_lugar", solicitud)
    return jsonify(creado), 201


# ===========================================================================
# 5. Audiovisuales / Servicios (proveedores y pedidos)
# ===========================================================================

@app.get("/proveedores")
def listar_proveedores():
    provs = datos.listar("proveedores")
    tipo = request.args.get("tipo")
    if tipo:
        provs = [p for p in provs if p["tipo"] == tipo]
    buscar = request.args.get("buscar")
    if buscar:
        provs = [p for p in provs if buscar.lower() in p["nombre"].lower()]
    return jsonify(paginar(provs))


@app.get("/eventos/<int:id_>/proveedores")
def proveedores_evento(id_):
    # proveedores que tienen pedidos en este evento
    pedidos = datos.filtrar("pedidos", evento_id=id_)
    ids = {p["proveedor_id"] for p in pedidos}
    provs = [p for p in datos.listar("proveedores") if p["id"] in ids]
    return jsonify(provs)


@app.post("/eventos/<int:ev_id>/proveedores/<int:prov_id>/contratar")
def contratar_proveedor(ev_id, prov_id):
    if datos.obtener("eventos", ev_id) is None:
        return error("NO_ENCONTRADO", "Evento no encontrado.", 404)
    if datos.obtener("proveedores", prov_id) is None:
        return error("NO_ENCONTRADO", "Proveedor no encontrado.", 404)
    contrato = {"evento_id": ev_id, "proveedor_id": prov_id, "estado": "contratado"}
    creado = datos.crear("contrataciones", contrato)
    return jsonify(creado), 201


@app.post("/eventos/<int:id_>/pedidos")
def crear_pedido(id_):
    if datos.obtener("eventos", id_) is None:
        return error("NO_ENCONTRADO", "Evento no encontrado.", 404)
    cuerpo = request.get_json(silent=True) or {}
    falta = requiere_campos(cuerpo, ["proveedor_id"])
    if falta:
        return error("CAMPO_OBLIGATORIO", f"El campo '{falta}' es obligatorio.",
                     400, {"campo": falta})

    prov = datos.obtener("proveedores", cuerpo["proveedor_id"])
    pedido = {
        "evento_id": id_,
        "proveedor_id": cuerpo["proveedor_id"],
        "proveedor_nombre": prov["nombre"] if prov else None,
        "necesidades": cuerpo.get("necesidades", []),
        "estado": "generado",
        "coste_estimado": cuerpo.get("coste_estimado"),
        "coste_definitivo": None,
    }
    creado = datos.crear("pedidos", pedido)
    return jsonify(creado), 201


@app.get("/eventos/<int:id_>/pedidos")
def pedidos_evento(id_):
    return jsonify(datos.filtrar("pedidos", evento_id=id_))


@app.put("/pedidos/<int:id_>/confirmar")
def confirmar_pedido(id_):
    cuerpo = request.get_json(silent=True) or {}
    falta = requiere_campos(cuerpo, ["coste_definitivo"])
    if falta:
        return error("CAMPO_OBLIGATORIO",
                     "Para confirmar un pedido hay que indicar 'coste_definitivo'.",
                     400, {"campo": falta})
    actualizado = datos.actualizar("pedidos", id_, {
        "estado": "confirmado",
        "coste_definitivo": cuerpo["coste_definitivo"],
    })
    if actualizado is None:
        return error("NO_ENCONTRADO", "Pedido no encontrado.", 404)
    return jsonify(actualizado)


# ===========================================================================
# 6. Presupuesto
# ===========================================================================

@app.get("/eventos/<int:id_>/presupuesto")
def presupuesto_evento(id_):
    presus = datos.filtrar("presupuestos", evento_id=id_)
    if not presus:
        return error("NO_ENCONTRADO", "Este evento no tiene presupuesto.", 404)
    p = presus[0]
    total_ejecutado = sum(part["ejecutado"] for part in p["partidas"])
    respuesta = {
        "evento_id": id_,
        "total_presupuestado": p["total_presupuestado"],
        "total_ejecutado": round(total_ejecutado, 2),
        "partidas": p["partidas"],
    }
    return jsonify(respuesta)


@app.put("/eventos/<int:id_>/presupuesto")
def actualizar_presupuesto(id_):
    cuerpo = request.get_json(silent=True) or {}
    presus = datos.filtrar("presupuestos", evento_id=id_)
    if not presus:
        return error("NO_ENCONTRADO", "Este evento no tiene presupuesto.", 404)
    # actualizamos partidas si vienen
    for p in datos._datos["presupuestos"]:
        if p["evento_id"] == id_:
            if "partidas" in cuerpo:
                p["partidas"] = cuerpo["partidas"]
            if "total_presupuestado" in cuerpo:
                p["total_presupuestado"] = cuerpo["total_presupuestado"]
            return jsonify(p)
    return error("NO_ENCONTRADO", "No encontrado.", 404)


# ===========================================================================
# 7. Ponentes
# ===========================================================================

@app.get("/eventos/<int:id_>/ponentes")
def ponentes_de_evento(id_):
    relaciones = datos.filtrar("ponentes_evento", evento_id=id_)
    resultado = []
    for rel in relaciones:
        ponente = datos.obtener("ponentes", rel["ponente_id"])
        if ponente:
            resultado.append({
                "id": ponente["id"],
                "nombre": ponente["nombre"],
                "empresa": ponente["empresa"],
                "rol": rel["rol"],
                "estado": rel["estado"],
                "documentacion": rel["documentacion"],
                "ponencia": rel["ponencia"],
                "viajes": rel["viajes"],
                "facturacion": rel["facturacion"],
            })
    return jsonify(paginar(resultado))


@app.get("/ponentes/<int:id_>")
def detalle_ponente(id_):
    ponente = datos.obtener("ponentes", id_)
    if ponente is None:
        return error("NO_ENCONTRADO", "Ponente no encontrado.", 404)
    return jsonify(ponente)


@app.post("/ponentes")
def crear_ponente():
    cuerpo = request.get_json(silent=True) or {}
    falta = requiere_campos(cuerpo, ["nombre"])
    if falta:
        return error("CAMPO_OBLIGATORIO", f"El campo '{falta}' es obligatorio.",
                     400, {"campo": falta})
    nuevo = {
        "nombre": cuerpo["nombre"],
        "empresa": cuerpo.get("empresa"),
        "cargo": cuerpo.get("cargo"),
        "email": cuerpo.get("email"),
        "telefono": cuerpo.get("telefono"),
    }
    creado = datos.crear("ponentes", nuevo)
    return jsonify(creado), 201


@app.post("/eventos/<int:id_>/ponentes")
def asignar_ponente(id_):
    if datos.obtener("eventos", id_) is None:
        return error("NO_ENCONTRADO", "Evento no encontrado.", 404)
    cuerpo = request.get_json(silent=True) or {}
    falta = requiere_campos(cuerpo, ["ponente_id"])
    if falta:
        return error("CAMPO_OBLIGATORIO", f"El campo '{falta}' es obligatorio.",
                     400, {"campo": falta})
    # evitar duplicados
    ya = datos.filtrar("ponentes_evento", evento_id=id_, ponente_id=cuerpo["ponente_id"])
    if ya:
        return error("CONFLICTO", "Ese ponente ya está asignado a este evento.", 409)

    relacion = {
        "evento_id": id_,
        "ponente_id": cuerpo["ponente_id"],
        "rol": cuerpo.get("rol", "ponencia"),
        "estado": "invitado",
        "documentacion": "sin-iniciar",
        "ponencia": cuerpo.get("ponencia", {}),
        "viajes": "sin-iniciar",
        "facturacion": "sin-datos",
    }
    creado = datos.crear("ponentes_evento", relacion)
    return jsonify(creado), 201


@app.put("/ponentes/<int:id_>")
def editar_ponente(id_):
    cuerpo = request.get_json(silent=True) or {}
    actualizado = datos.actualizar("ponentes", id_, cuerpo)
    if actualizado is None:
        return error("NO_ENCONTRADO", "Ponente no encontrado.", 404)
    return jsonify(actualizado)


@app.get("/ponentes/<int:id_>/documentos")
def documentos_ponente(id_):
    return jsonify(datos.filtrar("documentos", ponente_id=id_))


@app.post("/ponentes/<int:id_>/documentos")
def subir_documento(id_):
    if datos.obtener("ponentes", id_) is None:
        return error("NO_ENCONTRADO", "Ponente no encontrado.", 404)
    cuerpo = request.get_json(silent=True) or {}
    falta = requiere_campos(cuerpo, ["tipo"])
    if falta:
        return error("CAMPO_OBLIGATORIO", f"El campo '{falta}' es obligatorio.",
                     400, {"campo": falta})
    doc = {
        "ponente_id": id_,
        "tipo": cuerpo["tipo"],
        "estado": cuerpo.get("estado", "recibido"),
        "archivo_url": cuerpo.get("archivo_url"),
    }
    creado = datos.crear("documentos", doc)
    return jsonify(creado), 201


@app.get("/ponentes/<int:id_>/viajes")
def viajes_ponente(id_):
    # buscamos la relación ponente-evento para leer el estado de viajes
    rels = datos.filtrar("ponentes_evento", ponente_id=id_)
    if not rels:
        return error("NO_ENCONTRADO", "Ese ponente no está en ningún evento.", 404)
    return jsonify({"ponente_id": id_, "estado": rels[0]["viajes"]})


@app.get("/ponentes/<int:id_>/facturacion")
def facturacion_ponente(id_):
    rels = datos.filtrar("ponentes_evento", ponente_id=id_)
    if not rels:
        return error("NO_ENCONTRADO", "Ese ponente no está en ningún evento.", 404)
    return jsonify({"ponente_id": id_, "estado": rels[0]["facturacion"]})


# ===========================================================================
# 8. Endpoints que usa la IA (agentes)
# ===========================================================================

@app.post("/borradores")
def crear_borrador():
    cuerpo = request.get_json(silent=True) or {}
    falta = requiere_campos(cuerpo, ["evento_id", "asunto", "cuerpo"])
    if falta:
        return error("CAMPO_OBLIGATORIO", f"El campo '{falta}' es obligatorio.",
                     400, {"campo": falta})
    borrador = {
        "evento_id": cuerpo["evento_id"],
        "ponente_id": cuerpo.get("ponente_id"),
        "tipo": cuerpo.get("tipo", "comunicacion"),
        "asunto": cuerpo["asunto"],
        "cuerpo": cuerpo["cuerpo"],
        "estado": "pendiente-validacion",
        "generado_por": cuerpo.get("generado_por", "agente"),
    }
    creado = datos.crear("borradores", borrador)
    return jsonify(creado), 201


@app.get("/borradores")
def listar_borradores():
    evento_id = request.args.get("evento", type=int)
    if evento_id is not None:
        return jsonify(datos.filtrar("borradores", evento_id=evento_id))
    return jsonify(datos.listar("borradores"))


@app.put("/borradores/<int:id_>/aprobar")
def aprobar_borrador(id_):
    actualizado = datos.actualizar("borradores", id_, {"estado": "aprobado"})
    if actualizado is None:
        return error("NO_ENCONTRADO", "Borrador no encontrado.", 404)
    # aquí, en producción, se enviaría el email de verdad
    return jsonify(actualizado)


@app.put("/borradores/<int:id_>/rechazar")
def rechazar_borrador(id_):
    actualizado = datos.actualizar("borradores", id_, {"estado": "rechazado"})
    if actualizado is None:
        return error("NO_ENCONTRADO", "Borrador no encontrado.", 404)
    return jsonify(actualizado)


@app.post("/bloqueos")
def crear_bloqueo():
    cuerpo = request.get_json(silent=True) or {}
    falta = requiere_campos(cuerpo, ["evento_id", "motivo"])
    if falta:
        return error("CAMPO_OBLIGATORIO", f"El campo '{falta}' es obligatorio.",
                     400, {"campo": falta})
    bloqueo = {
        "evento_id": cuerpo["evento_id"],
        "ponente_id": cuerpo.get("ponente_id"),
        "motivo": cuerpo["motivo"],
        "gravedad": cuerpo.get("gravedad", "media"),
        "detectado_por": cuerpo.get("detectado_por", "agente"),
    }
    creado = datos.crear("bloqueos", bloqueo)
    return jsonify(creado), 201


@app.get("/eventos/<int:id_>/bloqueos")
def bloqueos_evento(id_):
    return jsonify(datos.filtrar("bloqueos", evento_id=id_))


@app.post("/briefing/analizar")
def analizar_briefing():
    """
    Recibe un resumen (en la demo, texto) y devuelve campos del evento.
    Aquí va simulado: el equipo de data science sustituye este cuerpo
    por la llamada real al agente que lee el PDF/DOC y extrae los datos.
    """
    cuerpo = request.get_json(silent=True) or {}
    # respuesta simulada de ejemplo
    return jsonify({
        "campos": {
            "nombre": "Congreso Anual Industria",
            "cliente": "Cámara de Comercio",
            "tipo": "congreso",
            "num_personas": 320,
            "fecha_inicio": "2026-07-14",
            "fecha_fin": "2026-07-15",
        },
        "confianza": "alta",
        "avisos": ["Datos de ejemplo: sustituir por el agente real."],
    })


# ===========================================================================
# 9. Consulta genérica de solo lectura — Lumen (Agente 04 · Copilot)
# ===========================================================================
# Lumen es un agente conversacional que responde preguntas del equipo de
# Mitumi sobre los datos de la plataforma. Solo lee: nunca crea, actualiza
# ni borra nada. En vez de darle acceso a los endpoints de escritura de
# arriba, expone un único endpoint de solo lectura sobre datos.consultar().
#
# Lumen también puede usarse en modo local (MVP del orquestador) importando
# datos.py directamente y llamando a datos.consultar(...) / datos.tablas_consultables()
# sin pasar por HTTP.

@app.get("/consulta")
def consulta_generica():
    """
    GET /consulta                          -> tablas disponibles para consultar
    GET /consulta?tabla=eventos            -> todos los registros de esa tabla
    GET /consulta?tabla=eventos&estado=... -> registros filtrados por criterios
    """
    tabla = request.args.get("tabla")

    if tabla is None:
        return jsonify({"tablas_disponibles": datos.tablas_consultables()})

    criterios = {k: v for k, v in request.args.items() if k != "tabla"}
    resultado = datos.consultar(tabla, **criterios)

    if resultado is None:
        return error("TABLA_NO_ENCONTRADA",
                     f"La tabla '{tabla}' no existe o no es consultable.",
                     404, {"tablas_disponibles": datos.tablas_consultables()})

    return jsonify(paginar(resultado) if isinstance(resultado, list) else resultado)


# ===========================================================================
# Raíz: pequeña ayuda para saber que la API está viva
# ===========================================================================

@app.get("/")
def inicio():
    return jsonify({
        "api": "Gestión de eventos y ponentes",
        "estado": "en marcha",
        "prueba": "GET /eventos",
    })


# Manejador para rutas que no existen
@app.errorhandler(404)
def no_encontrado(e):
    return error("RUTA_NO_ENCONTRADA", "Esa ruta no existe.", 404)


if __name__ == "__main__":
    # debug=True recarga solo al guardar cambios (cómodo mientras desarrolláis)
    app.run(debug=True, port=5000)
