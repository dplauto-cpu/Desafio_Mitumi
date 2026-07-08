"""Convocatorias de ejemplo (simuladas) para probar el pipeline sin depender de que haya
novedades ese día en KontratazioA (ver sección 7 del build brief).

Tienen la misma forma que los diccionarios "crudos" que devuelve
sources.obtener_convocatorias(), para poder alimentar directamente
extractor.extraer_convocatoria().
"""

# creo una lista con tres convocatorias de ejemplo para probar sin depender de la web
EJEMPLOS: list[dict] = [
    # Claramente relevante: congreso institucional, encaja de lleno con el perfil de Mitumi.
    # primer ejemplo: un congreso que sí encaja con Mitumi
    {
        "diputacion": "Araba",
        "objeto": (
            "Servicio de organización integral y secretaría técnica del Congreso "
            "Institucional sobre Transición Energética 2026, incluyendo gestión del "
            "espacio, ponentes, catering y modalidad híbrida."
        ),
        "enlace_pliego": "https://www.contratacion.euskadi.eus/ejemplo/congreso-transicion-energetica",
        "id_expediente": "EJEMPLO-2026-0000001",
        "fecha_publicacion": "05/07/2026",
        "tipo_contrato": "Servicios",
        "estado_tramitacion": "Abierto / Plazo de presentación",
        "plazo_presentacion": "30/07/2026 23:59:00",
        "importe": "45.000,00",
        "organo_convocante": "Diputación Foral de Álava",
        "entidad_impulsora": "Departamento de Desarrollo Económico y Sostenibilidad",
    },
    # Claramente NO relevante: obra pública, fuera del perfil de Mitumi.
    # segundo ejemplo: una obra de carretera que no encaja
    {
        "diputacion": "Gipuzkoa",
        "objeto": (
            "Obras de renovación del firme y del sistema de drenaje en la carretera "
            "GI-2132, tramo Azpeitia-Azkoitia."
        ),
        "enlace_pliego": "https://www.contratacion.euskadi.eus/ejemplo/obras-gi2132",
        "id_expediente": "EJEMPLO-2026-0000002",
        "fecha_publicacion": "03/07/2026",
        "tipo_contrato": "Obras",
        "estado_tramitacion": "Abierto / Plazo de presentación",
        "plazo_presentacion": "20/08/2026 23:59:00",
        "importe": "1.230.000,00",
        "organo_convocante": "Diputación Foral de Gipuzkoa",
        "entidad_impulsora": "Departamento de Movilidad e Infraestructuras Viarias",
    },
    # Claramente NO relevante: suministro médico, fuera del perfil de Mitumi.
    # tercer ejemplo: un suministro sanitario que no encaja
    {
        "diputacion": "Bizkaia",
        "objeto": "Suministro de material sanitario fungible para centros de la Diputación Foral de Bizkaia.",
        "enlace_pliego": "https://www.contratacion.euskadi.eus/ejemplo/suministro-sanitario",
        "id_expediente": "EJEMPLO-2026-0000003",
        "fecha_publicacion": "01/07/2026",
        "tipo_contrato": "Suministros",
        "estado_tramitacion": "Abierto / Plazo de presentación",
        "plazo_presentacion": "15/07/2026 23:59:00",
        "importe": "89.500,00",
        "organo_convocante": "Diputación Foral de Bizkaia",
        "entidad_impulsora": "Departamento de Acción Social",
    },
]
