# knowledge/field_aliases.py

FIELD_ALIASES = {

    # ===== TABLA: clientes =====
    "cliente": [
        "cliente",
        "empresa",
        "organizador",
        "nombre del cliente",
        "razón social"
    ],
    "email_cliente": [
        "email",
        "correo",
        "mail",
        "email de contacto"
    ],
    "telefono_cliente": [
        "teléfono",
        "telefono",
        "móvil",
        "contacto telefónico"
    ],
    "sector_cliente": [
        "sector cliente",
        "sector de la empresa",
        "industria"
    ],
    "ciudad_cliente": [
        "ciudad del cliente",
        "localidad cliente"
    ],

    # ===== TABLA: eventos =====
    "nombre_evento": [
        "nombre del evento",
        "evento",
        "nombre",
        "título del evento",
        "título"
    ],
    "ciudad": [
        "ciudad",
        "localidad",
        "municipio",
        "ubicación",
        "lugar"
    ],
    "lugar_confirmado": [
        "lugar confirmado",
        "espacio confirmado",
        "ubicación confirmada",
        "sala confirmada"
    ],
    "fecha_inicio": [
        "fecha inicio",
        "fecha de inicio",
        "inicio",
        "fecha desde",
        "desde"
    ],
    "fecha_fin": [
        "fecha fin",
        "fecha de fin",
        "fin",
        "fecha hasta",
        "hasta"
    ],
    "numero_personas": [
        "número de asistentes",
        "numero de asistentes",
        "aforo",
        "asistentes",
        "nº personas",
        "numero personas",
        "cantidad de personas"
    ],
    "tipo_evento": [
        "tipo de evento",
        "formato",
        "categoría",
        "categoria",
        "clasificación"
    ],
    "nota": [
        "nota",
        "observaciones",
        "comentarios",
        "notas adicionales"
    ],

    # ===== TABLA: presupuestos =====
    "estado_presupuesto": [
        "estado del presupuesto",
        "estado",
        "situación"
    ],
    "total": [
        "total",
        "importe total",
        "coste total",
        "precio total"
    ],
    "fecha_presupuesto": [
        "fecha presupuesto",
        "fecha del presupuesto"
    ],
    "nota_ubicacion": [
        "nota ubicación",
        "observaciones ubicación",
        "comentarios espacio"
    ],
    "precio_ubicacion": [
        "precio ubicación",
        "coste espacio",
        "alquiler sala"
    ],
    "precio_catering": [
        "precio catering",
        "coste catering",
        "importe comida"
    ],
    "precio_audiovisuales": [
        "precio audiovisuales",
        "coste AV",
        "importe sonido"
    ],
    "precio_otros": [
        "precio otros",
        "costes adicionales",
        "extras presupuesto"
    ],
    "nota_catering": [
        "nota catering",
        "comentarios catering",
        "observaciones comida"
    ],
    "nota_audiovisuales": [
        "nota audiovisuales",
        "comentarios AV",
        "observaciones sonido"
    ],
    "nota_otros": [
        "nota otros",
        "comentarios extras",
        "observaciones adicionales"
    ],
    "observaciones": [
        "observaciones",
        "notas del presupuesto",
        "comentarios"
    ],

    # ===== TABLA: ponentes =====
    "nombre_ponente": [
        "ponente",
        "nombre del ponente",
        "conferenciante",
        "nombre",
        "speaker"
    ],
    "docu_identificacion": [
        "documento identificación",
        "dni",
        "nie",
        "documento",
        "identificación"
    ],
    "email_ponente": [
        "email ponente",
        "correo ponente",
        "mail ponente"
    ],
    "sector_ponente": [
        "sector",
        "área",
        "especialidad",
        "campo"
    ],
    "telefono_ponente": [
        "teléfono ponente",
        "telefono ponente",
        "móvil ponente"
    ],
    "foto_link": [
        "foto",
        "imagen",
        "link foto",
        "url foto"
    ],
    "cv_link": [
        "cv",
        "currículum",
        "link cv",
        "url cv"
    ],
    "empresa_ponente": [
        "empresa del ponente",
        "organización",
        "compañía"
    ],
    "cargo_ponente": [
        "cargo",
        "puesto",
        "rol",
        "posición"
    ],

    # ===== TABLA: evento_ponente =====
    "nombre_hotel": [
        "hotel",
        "nombre del hotel",
        "alojamiento"
    ],
    "nota_transporte": [
        "nota transporte",
        "observaciones transporte",
        "comentarios traslados"
    ],
    "horario_ida_transporte": [
        "hora ida transporte",
        "ida transporte",
        "salida transporte"
    ],
    "horario_vuelta_transporte": [
        "hora vuelta transporte",
        "vuelta transporte",
        "regreso transporte"
    ],
    "localizacion_hotel": [
        "localización hotel",
        "dirección hotel"
    ],
    "horario_ponencia": [
        "hora ponencia",
        "horario de ponencia",
        "turno ponencia"
    ],
    "checkin_horario": [
        "checkin",
        "hora checkin",
        "registro"
    ],
    "ponente_estado": [
        "estado ponente",
        "confirmación ponente"
    ],
    "presentacion_link": [
        "presentación",
        "link presentación",
        "ppt",
        "diapositivas"
    ],
    "billete_ida_link": [
        "billete ida",
        "link ida",
        "transporte ida"
    ],
    "billete_vuelta_link": [
        "billete vuelta",
        "link vuelta",
        "transporte vuelta"
    ],
    "tipo_ponencia": [
        "tipo de ponencia",
        "modalidad",
        "formato ponencia"
    ],

    # ===== TABLA: salas (NUEVA) =====
    "nombre_sala": [
        "nombre sala",
        "sala",
        "auditorio",
        "espacio"
    ],
    "tipo_sala": [
        "tipo sala",
        "categoría sala"
    ],
    "capacidad_max_sala": [
        "capacidad máxima",
        "aforo máximo",
        "capacidad sala"
    ],
    "nota_sala": [
        "nota sala",
        "observaciones sala"
    ],

    # ===== TABLA: espacios =====
    "nombre_espacio": [
        "nombre espacio",
        "espacio",
        "sala",
        "auditorio"
    ],
    "direccion_espacio": [
        "dirección",
        "dirección espacio"
    ],
    "capacidad_total": [
        "capacidad",
        "capacidad total",
        "aforo total"
    ],
    "aforo_espacio": [
        "aforo",
        "aforo espacio"
    ],
    "telefono_contacto_espacio": [
        "teléfono contacto",
        "contacto teléfono"
    ],
    "nombre_contacto_espacio": [
        "nombre contacto",
        "contacto"
    ],
    "email_contacto_espacio": [
        "email contacto",
        "correo contacto"
    ],

    # ===== TABLA: estados =====
    "descripcion_estado": [
        "estado",
        "descripción estado",
        "situación"
    ]
}
