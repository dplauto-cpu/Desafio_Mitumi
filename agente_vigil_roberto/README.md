# Vigil (versión plataforma) — agente de alertas de licitaciones para Mitumi

Vigil es un agente que, cada mañana, consulta la Plataforma de Contratación
Pública de Euskadi (KontratazioA) para las tres diputaciones forales
(Araba, Gipuzkoa y Bizkaia), filtra las licitaciones relevantes para Mitumi
(agencia de eventos) usando un modelo de lenguaje, y **publica el resultado
hacia la plataforma Mitumi BackStage** (sección "Concursos Públicos").

Esta versión **no envía email**: en su lugar genera un fichero JSON (más un
`.ics` por concurso) que la plataforma lee. Es la variante "solo plataforma".

## Funcionalidades

- **⏱️ Semáforo de urgencia**: cada concurso incluye los días hábiles que
  quedan y su nivel (alta/media/baja) (`urgency.py`).
- **🔄 Detector de modificaciones**: si un concurso ya avisado cambia (p. ej.
  amplían el plazo), se marca como modificación (`dedupe.py`).
- **🏷️ Etiquetado temático**: el LLM añade etiquetas (Institucional, Cultura,
  Gastronomía…) para repartir la revisión por áreas (`relevance.py`).
- **📅 Calendario `.ics`**: cada concurso lleva un archivo de calendario para
  que la plataforma ofrezca añadir el plazo a la agenda (`calendar_ics.py`).

## Registro histórico y API (integración con la plataforma)

Además del JSON diario, Vigil **acumula un histórico** de todos los concursos
encontrados —relevantes o no— en la tabla `concursos` del mismo `vigil.db`
(`history.py`). Cada concurso guarda sus datos, si fue relevante para Mitumi, su
urgencia y el plazo en formato ISO para poder ordenar y filtrar.

Para que la plataforma (que construye el equipo full-stack) lo consuma, hay una
pequeña **API HTTP** (`api.py`, Flask). Se arranca así:

```bash
waitress-serve --port=8000 vigil.api:app
```

Endpoints:

- `GET /concursos` — consulta el histórico con filtros de query string:
  `q` (texto en objeto/órgano), `diputacion`, `urgencia`, `en_plazo` (bool,
  "solo los que siguen en plazo"), `relevante` (bool), `limite`, `offset`.
- `POST /ejecuciones` — **lanza el agente en vivo** (scrape + LLM) en segundo
  plano; es el "botón de búsqueda al instante". Devuelve un `id` y `estado`.
- `GET /ejecuciones/{id}` — estado de esa ejecución (`en_curso` / `terminada` /
  `error`) y cuántos concursos nuevos añadió, para hacer *polling* desde la UI.
- `GET /health` — sonda de vida.

El seguimiento de ejecuciones se guarda en memoria (se reinicia con el servidor);
suficiente para un disparo puntual desde un botón.

## Modo demo (enseñar el agente sin web ni Groq)

Para mostrar el agente funcionando —p. ej. al equipo full-stack— sin depender de
`GROQ_API_KEY`, de Playwright ni de que la web tenga novedades ese día, se activa
el **modo demo** con la variable `VIGIL_DEMO=1`. Usa las convocatorias de ejemplo
de `vigil/examples/` y salta el LLM (`demo.py`), pero recorre **el mismo pipeline**
(dedupe → estructurar → relevancia → urgencia → histórico → JSON + API).

La forma más simple de enseñarlo es con un único comando, que carga los datos de
ejemplo (si hacen falta) y levanta la web + la API:

```powershell
python serve_demo.py
```

Luego abre **`http://127.0.0.1:8000/`** → una web con los concursos en tarjetas,
buscador, filtros (diputación, urgencia, "solo en plazo", "solo relevantes") y el
botón **"Actualizar ahora"**, que lanza el agente en vivo (en demo, ~1 s). Esta web
sirve de referencia visual para el equipo full-stack; la propia API queda en la
misma dirección (`/concursos`, `/ejecuciones`, `/docs`).

Usa una base de datos y una salida de demo aparte (`vigil_demo.db`, `salida_demo/`),
así que **no toca los datos reales**. Para el agente **real**, quita `VIGIL_DEMO` y
pon `GROQ_API_KEY`.

## El contrato de salida (lo que lee la plataforma)

Al ejecutarse, el agente escribe en la carpeta `salida/`:

- `salida/concursos.json` → lista de concursos relevantes del día, cada uno
  con título, organismo, fechas, importe, urgencia, etiquetas, si es una
  modificación, el motivo de encaje y la ruta a su `.ics`.
- `salida/ics/*.ics` → un archivo de calendario por concurso.

La carpeta se puede cambiar con la variable de entorno `VIGIL_OUTPUT_DIR`.
Cuando la plataforma defina su mecanismo (API REST o base de datos), solo hay
que adaptar `publisher.py` para enviar ese mismo JSON por el nuevo canal.

## Cómo funciona (flujo)

1. **sources.py** → lee la web de KontratazioA con Playwright y saca las convocatorias de las 3 diputaciones.
2. **dedupe.py** → detecta si cada convocatoria es nueva, una modificación o ya vista (SQLite).
3. **extractor.py** → convierte cada convocatoria en datos limpios (Groq + Pydantic).
4. **relevance.py** → decide si encaja con el perfil de Mitumi, explica por qué y pone etiquetas.
5. **urgency.py** → calcula el semáforo de urgencia según el plazo.
6. **calendar_ics.py** → genera el archivo de calendario de cada concurso.
7. **history.py** → guarda cada concurso encontrado (relevante o no) en el histórico SQLite.
8. **publisher.py** → escribe el JSON y los `.ics` en `salida/` para la plataforma.
9. **main.py** → orquesta todo el proceso de principio a fin.
10. **api.py** → expone el histórico y el disparador de ejecución a la plataforma (Flask).

## Instalación

```bash
# creo un entorno virtual de Python
python -m venv .venv
# lo activo (Windows)
.venv\Scripts\activate
# instalo las librerías
pip install -r requirements.txt
# descargo el navegador que usa Playwright
playwright install chromium
```

## Cómo ejecutarlo a mano

Necesita esta variable de entorno:

- `GROQ_API_KEY` — clave de la API de Groq

Y de forma opcional:

- `VIGIL_OUTPUT_DIR` — carpeta donde escribir la salida (por defecto `salida/`)

Con eso puesto:

```bash
python -m vigil.main
```

Al terminar, revisa `salida/concursos.json` y `salida/ics/`.

## Tests

```bash
pytest vigil/tests
```

## Nota sobre la automatización diaria

El fichero `.github/workflows/vigil.yml` define la ejecución automática cada
mañana con GitHub Actions. **Solo funciona si este proyecto está en la raíz
de su propio repositorio** (GitHub ignora los workflows que están dentro de
subcarpetas). En el repositorio definitivo del proyecto habrá que colocarlo
en la raíz y configurar las credenciales como *secrets* del repo.
