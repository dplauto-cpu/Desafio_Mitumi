# streamlit_app.py
# =====================================================================
# INTERFAZ DE PRUEBA PARA EL AGENTE OPERIS - VERSIÓN CORREGIDA V2
# =====================================================================
# Esta aplicación Streamlit permite probar el agente Operis con:
#   - Subida de archivos (.txt, .pdf, .docx)
#   - Pegado de texto manual
#   - Selección entre motor de reglas (gratis) y motor LLM (Groq)
#   - Visualización de los 6 bloques de salida en pestañas
#   - Validación de campos obligatorios
#   - Descarga del JSON de salida
#   - Historial de las últimas 5 extracciones
#
# Uso:
#   streamlit run streamlit_app.py
# =====================================================================

import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import tempfile
import os

# Configuración de la página (debe ser lo primero)
st.set_page_config(
    page_title="Agente Operis - Pruebas",
    page_icon="📋",
    layout="wide"
)

# ---------------------------------------------------------------------
# 1. IMPORTACIONES DEL PROYECTO
# ---------------------------------------------------------------------
import sys
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.nucleo import ejecutar_agente
from src.funciones import leer_archivo
from src.schemas import CAMPOS_OBLIGATORIOS_EVENTO
from config import settings


# ---------------------------------------------------------------------
# 2. ESTILO CSS
# ---------------------------------------------------------------------
st.markdown("""
<style>
    html, body, .stApp {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    .main-title {
        font-size: 24px;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 8px;
    }
    .sub-title {
        font-size: 16px;
        color: #555555;
        margin-bottom: 24px;
    }
    .field-label {
        font-size: 14px;
        font-weight: 600;
        color: #2c2c2c;
        margin-bottom: 4px;
    }
    .field-value {
        font-size: 13px;
        color: #1a1a1a;
        background-color: #f5f5f5;
        padding: 6px 10px;
        border-radius: 4px;
        border-left: 3px solid #4a90d9;
        margin-bottom: 8px;
        font-family: 'Courier New', monospace;
    }
    .field-empty {
        font-size: 13px;
        color: #aaaaaa;
        background-color: #f9f9f9;
        padding: 6px 10px;
        border-radius: 4px;
        border-left: 3px solid #cccccc;
        margin-bottom: 8px;
        font-style: italic;
    }
    .block-card {
        background-color: #fafafa;
        border-radius: 8px;
        padding: 16px 18px;
        margin-bottom: 12px;
        border: 1px solid #e8e8e8;
    }
    .agent-notice {
        background-color: #fff8e1;
        border-radius: 6px;
        padding: 10px 16px;
        margin-bottom: 16px;
        border-left: 4px solid #f5a623;
        font-size: 14px;
        color: #5d4a0e;
    }
    .status-badge {
        display: inline-block;
        padding: 2px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .status-badge.success {
        background-color: #e6f7e6;
        color: #1a7a1a;
    }
    .status-badge.error {
        background-color: #fde8e8;
        color: #b33c3c;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 14px;
        padding: 8px 16px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# 3. FUNCIONES AUXILIARES
# ---------------------------------------------------------------------

def formatear_valor(valor):
    if valor is None or valor == "":
        return None
    return str(valor)


def mostrar_campo(nombre, valor):
    st.markdown(f'<div class="field-label">{nombre}</div>', unsafe_allow_html=True)
    valor_limpio = formatear_valor(valor)
    if valor_limpio:
        st.markdown(f'<div class="field-value">{valor_limpio}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="field-empty">(no detectado)</div>', unsafe_allow_html=True)


def mostrar_bloque(bloque):
    if not bloque:
        st.markdown('<div class="block-card"><i>No hay información en este bloque.</i></div>', unsafe_allow_html=True)
        return
    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    for campo, valor in bloque.items():
        mostrar_campo(campo.replace("_", " ").title(), valor)
    st.markdown('</div>', unsafe_allow_html=True)


def mostrar_ponentes(lista_ponentes):
    if not lista_ponentes or len(lista_ponentes) == 0:
        st.markdown('<div class="block-card"><i>No hay ponentes detectados.</i></div>', unsafe_allow_html=True)
        return
    for idx, ponente in enumerate(lista_ponentes, 1):
        st.markdown(f'<div class="block-card"><b>Ponente {idx}</b></div>', unsafe_allow_html=True)
        for campo, valor in ponente.items():
            mostrar_campo(campo.replace("_", " ").title(), valor)
        st.markdown("---")


def leer_archivo_subido(archivo_subido):
    """Lee un archivo subido a Streamlit usando la función leer_archivo() del agente."""
    if archivo_subido is None:
        return ""
    
    try:
        # Obtener extensión
        nombre = archivo_subido.name
        extension = nombre.split('.')[-1].lower()
        
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp:
            tmp.write(archivo_subido.getvalue())
            tmp_path = tmp.name
        
        # Leer con la función del agente
        texto = leer_archivo(tmp_path)
        
        # Limpiar
        os.unlink(tmp_path)
        
        return texto
    except Exception as e:
        st.error(f"Error al leer el archivo: {str(e)}")
        return ""


def calcular_porcentaje_completado(resultado):
    """
    % de CAMPOS_OBLIGATORIOS_EVENTO detectados, a partir de
    resultado["bloqueos_detectados"] (el contrato final de
    ejecutar_agente() no trae ya un porcentaje calculado -- solo la
    lista de campos pendientes, que además mezcla los obligatorios con
    3 informativos: cliente_nombre, cliente_empresa, espacio_nombre).
    """
    pendientes = resultado.get("bloqueos_detectados", [])
    pendientes_obligatorios = [c for c in pendientes if c in CAMPOS_OBLIGATORIOS_EVENTO]
    if not CAMPOS_OBLIGATORIOS_EVENTO:
        return 0
    detectados = len(CAMPOS_OBLIGATORIOS_EVENTO) - len(pendientes_obligatorios)
    return round(detectados / len(CAMPOS_OBLIGATORIOS_EVENTO) * 100)


# ---------------------------------------------------------------------
# 4. INICIALIZACIÓN DE SESIÓN
# ---------------------------------------------------------------------

if "historial" not in st.session_state:
    st.session_state.historial = []

if "resultado_actual" not in st.session_state:
    st.session_state.resultado_actual = None

# Valor original de GROQ_API_KEY cargado desde .env al arrancar la
# sesión, ANTES de que el sidebar pueda sobrescribir settings.GROQ_API_KEY
# con una clave pegada a mano. Se guarda en session_state (no en una
# variable de módulo) porque todo streamlit_app.py se re-ejecuta en
# cada rerun -- una variable de módulo se recalcularía cada vez
# leyendo settings.GROQ_API_KEY, que para ese momento ya podría estar
# mutada por el propio campo de texto del rerun anterior.
if "groq_api_key_desde_env" not in st.session_state:
    st.session_state.groq_api_key_desde_env = settings.GROQ_API_KEY

# ALMACENAMOS EL TEXTO DEL BRIEFING AQUÍ
if "texto_briefing" not in st.session_state:
    st.session_state.texto_briefing = ""

# NOMBRE DEL ARCHIVO ACTUAL (para mostrar)
if "nombre_archivo_actual" not in st.session_state:
    st.session_state.nombre_archivo_actual = ""

# Texto que se proceso la ULTIMA VEZ CON EXITO (para saber si el
# resultado en pantalla sigue correspondiendo a la fuente activa, o si
# es de un archivo/texto distinto y hay que ocultarlo -- ver más abajo).
if "ultimo_texto_procesado" not in st.session_state:
    st.session_state.ultimo_texto_procesado = None


# ---------------------------------------------------------------------
# 5. FUNCIÓN PARA PROCESAR EL TEXTO
# ---------------------------------------------------------------------

def procesar_texto(texto, motor):
    """Procesa el texto con el agente y guarda el resultado."""
    if not texto or not texto.strip():
        st.warning("No hay texto para procesar.")
        return
    
    payload = {
        "id_evento": None,
        "id_registro": None,
        "tipo_peticion": "extraer_briefing",
        "origen": "streamlit",
        "usuario_solicitante": "pruebas",
        "rol_usuario": "organizador",
        "datos": {
            "texto_briefing": texto,
            "motor": motor
        },
        "contexto": {},
        "modo": "propuesta"
    }
    
    with st.spinner("🔍 Extrayendo información..."):
        resultado = ejecutar_agente(payload)
    
    if resultado.get("ok", False):
        st.session_state.resultado_actual = resultado
        st.session_state.ultimo_texto_procesado = texto

        # Guardar en historial
        porcentaje = calcular_porcentaje_completado(resultado)
        st.session_state.historial.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "porcentaje": porcentaje,
            "motor": motor
        })
        if len(st.session_state.historial) > 5:
            st.session_state.historial = st.session_state.historial[-5:]
        
        st.success("✅ Extracción completada.")
    else:
        # Importante: borrar el resultado anterior. Si no, tras un
        # fallo (p. ej. motor "llm" sin GROQ_API_KEY) las pestañas de
        # abajo seguirían mostrando el último resultado que sí
        # funcionó -- dando la falsa impresión de que el documento
        # nuevo no se ha tenido en cuenta, cuando en realidad cada
        # intento nuevo está fallando.
        st.session_state.resultado_actual = None
        errores = resultado.get("errores", ["Error desconocido"])
        st.error(f"❌ Error en la extracción: {'; '.join(errores)}")


# ---------------------------------------------------------------------
# 6. INTERFAZ PRINCIPAL
# ---------------------------------------------------------------------

st.markdown('<div class="main-title">📋 Agente Operis — Extracción de briefings</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Sube un documento o pega el texto de un briefing para extraer la información estructurada.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------
# 6.1 Barra lateral
# ---------------------------------------------------------------------

with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    
    motor = st.selectbox(
        "Motor de extracción",
        options=["llm", "reglas"],
        index=0,
        help="llm: usa Groq (requiere API key) | reglas: gratuito y determinista"
    )

    api_key_manual = st.text_input(
        "GROQ_API_KEY",
        type="password",
        placeholder="Pégala aquí, o déjala vacía para usar la del .env",
        help="Solo para esta sesión de Streamlit -- no se guarda en ningún "
             "archivo ni sustituye al .env. Clave gratuita en console.groq.com",
        key="api_key_manual_input"
    )
    # Se recalcula en cada rerun a partir del campo de texto ACTUAL: si
    # se vacía el campo, se vuelve al valor de .env en vez de quedarse
    # con la última clave pegada (evita una "clave fantasma" que ya no
    # se ve en pantalla pero sigue activa).
    settings.GROQ_API_KEY = api_key_manual.strip() or st.session_state.groq_api_key_desde_env

    api_key_cargada = bool(settings.GROQ_API_KEY)
    if api_key_cargada:
        origen = "pegada arriba" if api_key_manual.strip() else "de .env"
        st.markdown(f'<span class="status-badge success">✅ API key cargada ({origen})</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge error">❌ API key no disponible</span>', unsafe_allow_html=True)
        if motor == "llm":
            st.warning("El motor LLM requiere una GROQ_API_KEY -- pégala arriba o defínela en .env")
    
    st.markdown("---")
    st.markdown("### 📜 Historial")
    
    if st.session_state.historial:
        for i, entry in enumerate(st.session_state.historial[-5:]):
            timestamp = entry.get("timestamp", "sin fecha")
            pct = entry.get("porcentaje", 0)
            motor_usado = entry.get("motor", "?")
            st.caption(f"{i+1}. {timestamp} — {pct}% ({motor_usado})")
    else:
        st.caption("Aún no hay extracciones guardadas.")
    
    if st.button("🗑️ Limpiar historial", use_container_width=True):
        st.session_state.historial = []
        st.session_state.resultado_actual = None
        st.session_state.texto_briefing = ""
        st.session_state.nombre_archivo_actual = ""
        st.rerun()


# ---------------------------------------------------------------------
# 6.2 Área principal
# ---------------------------------------------------------------------

# --- Columna izquierda: entrada ---
col_izq, col_der = st.columns([2, 1])

with col_izq:
    # Fuente del texto: una de las dos, nunca las dos a la vez. Antes,
    # el cuadro de texto manual se leía SIEMPRE (aunque tuviera texto
    # de una prueba anterior) y sobrescribía silenciosamente cualquier
    # archivo nuevo que se subiera después -- un widget de Streamlit
    # conserva su valor entre reruns hasta que se vacía a mano, así que
    # bastaba con haber pegado texto una vez para que ya no se pudiera
    # volver a usar la subida de archivo. Con una fuente explícita este
    # problema desaparece: solo se lee el widget de la fuente activa.
    fuente = st.radio(
        "Fuente del texto",
        options=["Subir archivo", "Pegar texto"],
        horizontal=True,
        key="fuente_texto"
    )

    texto_para_procesar = ""
    nombre_para_mostrar = ""

    if fuente == "Subir archivo":
        archivo = st.file_uploader(
            "Subir documento",
            type=["txt", "pdf", "docx"],
            help="Formatos soportados: .txt, .pdf, .docx",
            key="file_uploader_principal"
        )
        archivo_no_legible = False
        if archivo is not None:
            texto_leido = leer_archivo_subido(archivo)
            if texto_leido:
                texto_para_procesar = texto_leido
                nombre_para_mostrar = archivo.name
                st.info(f"📄 Archivo cargado: {archivo.name} ({len(texto_leido)} caracteres)")
            else:
                st.warning("El archivo no se pudo leer o está vacío.")
                archivo_no_legible = True
    else:
        texto_manual = st.text_area(
            "Pega el texto del briefing aquí",
            height=180,
            placeholder="Pega aquí el contenido del briefing (email, resumen, etc.)...",
            key="text_area_manual"
        )
        texto_para_procesar = texto_manual.strip()
        nombre_para_mostrar = "texto manual"
        archivo_no_legible = False

    # Si la fuente activa (archivo o texto) ya no es la misma que se
    # procesó la última vez con éxito, se oculta el resultado anterior
    # -- si no, tras un fallo de lectura o de extracción con un
    # archivo/texto NUEVO, las pestañas de abajo seguirían mostrando
    # los datos del último que sí funcionó, dando la falsa impresión
    # de que el nuevo documento no se ha tenido en cuenta.
    if (texto_para_procesar and texto_para_procesar != st.session_state.ultimo_texto_procesado) \
            or archivo_no_legible:
        st.session_state.resultado_actual = None

    # Solo se actualiza session_state si la fuente activa tiene
    # contenido -- así no se borra un resultado ya procesado solo
    # porque, por ejemplo, se cambió de pestaña de fuente sin rellenar
    # nada todavía en la nueva.
    if texto_para_procesar:
        st.session_state.texto_briefing = texto_para_procesar
        st.session_state.nombre_archivo_actual = nombre_para_mostrar

    # --- Botón ---
    if st.button("🚀 Procesar documento", type="primary", use_container_width=True):
        if texto_para_procesar:
            procesar_texto(texto_para_procesar, motor)
        else:
            st.warning("⚠️ No hay texto para procesar. Sube un archivo o pega un texto.")


# ---------------------------------------------------------------------
# 6.3 Mostrar resultados
# ---------------------------------------------------------------------

if st.session_state.resultado_actual:
    resultado = st.session_state.resultado_actual
    datos = resultado.get("datos_detectados", {})

    st.markdown("---")
    st.markdown("### 📊 Resultados de la extracción")

    # Barra de validación. El contrato final de ejecutar_agente() NO
    # tiene "_validacion"/"_aviso_agente" -- esas claves solo existen
    # DENTRO del motor, antes de que src/nucleo.py construya la
    # respuesta final (el % se "traduce" a bloqueos_detectados, la
    # lista de campos pendientes, y el aviso pasa a "resumen"). Leer
    # "_validacion" aquí siempre devolvía {} y el porcentaje siempre
    # salía 0, aunque el agente sí hubiera detectado datos.
    pendientes = resultado.get("bloqueos_detectados", [])
    porcentaje = calcular_porcentaje_completado(resultado)

    col_v1, col_v2 = st.columns([3, 1])
    with col_v1:
        st.progress(porcentaje / 100, text=f"Completado: {porcentaje}%")
        if pendientes:
            st.warning(f"Campos pendientes: {', '.join(pendientes)}")
        else:
            st.success("Todos los campos obligatorios han sido detectados.")

    with col_v2:
        # Botón de descarga JSON
        json_str = json.dumps(resultado, ensure_ascii=False, indent=2)
        st.download_button(
            label="💾 Descargar JSON",
            data=json_str,
            file_name=f"briefing_extraido_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

    # Aviso del agente (resultado["resumen"] -- antes se leía de
    # "_aviso_agente.mensaje", que tampoco existe en el contrato final)
    if resultado.get("resumen"):
        st.markdown(f'<div class="agent-notice">ℹ️ {resultado["resumen"]}</div>', unsafe_allow_html=True)

    # Pestañas
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📅 Evento",
        "👤 Cliente",
        "🏢 Espacio",
        "🪑 Sala",
        "💰 Presupuesto",
        "🎤 Ponentes",
        "📄 JSON"
    ])

    with tab1:
        mostrar_bloque(datos.get("evento", {}))

    with tab2:
        mostrar_bloque(datos.get("cliente", {}))

    with tab3:
        mostrar_bloque(datos.get("espacio", {}))

    with tab4:
        mostrar_bloque(datos.get("sala", {}))

    with tab5:
        mostrar_bloque(datos.get("presupuesto", {}))

    with tab6:
        mostrar_ponentes(datos.get("ponentes", []))

    with tab7:
        st.json(resultado)

else:
    st.info("ℹ️ Sube un documento o pega un briefing y pulsa 'Procesar documento'.")


# ---------------------------------------------------------------------
# 7. PIE DE PÁGINA
# ---------------------------------------------------------------------
st.markdown("---")
st.caption("Agente Operis — Motor de extracción de briefings | Streamlit v1.2")