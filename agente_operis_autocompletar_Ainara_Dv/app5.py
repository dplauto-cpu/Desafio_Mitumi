import streamlit as st
#from autofill_agent import extraer_briefing
from briefing_agent import extraer_briefing

import json
import os
from datetime import datetime

st.set_page_config(
    page_title="Agente Autorrellenado",
    layout="wide"
)

st.title("🤖 Agente de Autorrellenado")

st.subheader("Briefing inicial")


archivo = st.file_uploader(
    "Subir briefing del evento",
    type=["txt"]
)

texto_archivo = ""

if archivo is not None:
    texto_archivo = archivo.read().decode("utf-8")


texto = st.text_area(
    "Pega aquí el texto del evento",
    value=texto_archivo,
    height=220,
    placeholder="Pega aquí el briefing del evento..."
)



#texto = st.text_area(
#    "Pega aquí el texto del evento",
#    height=220,
#    placeholder="Pega aquí el briefing del evento..."
#)

if st.button("Autocompletar"):           ### Analizar briefing
    datos = extraer_briefing(texto)
    st.session_state["datos"] = datos


datos = st.session_state.get("datos", {})

if datos:
    st.subheader("🤖 Informe del análisis del briefing")

    st.write(
        "El agente ha finalizado el análisis del documento y ha generado "
        "una propuesta de información para la creación del evento."
    )


    st.markdown("""
    <div style="
        background-color:#FCE4EC;
        padding:15px;
        border-left:6px solid #E91E63;
        border-radius:8px;
        color:#880E4F;
        font-size:16px;
    ">
    <b>⚠️ Revisión obligatoria</b><br>
    Revise los datos detectados antes de confirmar la creación del evento.
    </div>
    """, unsafe_allow_html=True)




    #st.info(
    #    "Revise los datos detectados antes de confirmar la creación del evento."
    #)

    if "_validacion" in datos:
        st.info(
            f"Completado: {datos['_validacion']['porcentaje_completado']}%"
        )

        if datos["_validacion"]["campos_pendientes"]:
            st.warning(
                "Campos pendientes: "
                + ", ".join(datos["_validacion"]["campos_pendientes"])
            )
        else:
            st.success("Todos los campos obligatorios han sido detectados.")




#st.subheader("Datos detectados")
st.subheader("📋 Información extraída por el agente")

#st.info(
#    "⚠️ El agente propone estos datos automáticamente. "
#    "Revísalos y corrígelos si es necesario antes de confirmar la creación del evento."
#)


nombre_evento = st.text_input("Nombre del evento", datos.get("nombre_evento", ""))
cliente = st.text_input("Cliente", datos.get("cliente", ""))
tipo_evento = st.text_input("Tipo de evento", datos.get("tipo_evento", ""))
numero_personas = st.text_input("Número de personas", datos.get("numero_personas", ""))
fecha_inicio = st.text_input("Fecha inicio", datos.get("fecha_inicio", ""))
fecha_fin = st.text_input("Fecha fin", datos.get("fecha_fin", ""))
ciudad = st.text_input("Ciudad", datos.get("ciudad", ""))
estado_presupuesto = st.text_input("Estado del presupuesto", datos.get("estado_presupuesto", ""))






if st.button("✅ Confirmar y crear evento"):
    evento = {
        "nombre_evento": nombre_evento,
        "cliente": cliente,
        "tipo_evento": tipo_evento,
        "numero_personas": numero_personas,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "ciudad": ciudad,
        "estado_presupuesto": estado_presupuesto,
        "estado_validacion": "validado_por_usuario"
    }

    os.makedirs("data/events", exist_ok=True)

    nombre_archivo = f"data/events/evento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(evento, f, ensure_ascii=False, indent=4)

    st.success("Evento confirmado y guardado correctamente.")
    st.json(evento)
