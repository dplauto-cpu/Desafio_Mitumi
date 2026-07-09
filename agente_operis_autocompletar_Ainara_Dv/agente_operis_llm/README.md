# agente_operis — Autocompletado de briefings de eventos

> **Esta es la copia `agente_operis_llm/`: motor `llm` (Groq) configurado por
> defecto en `.env`** (`OPERIS_MOTOR=llm`), para probar la extracción con IA
> real. La copia hermana `Agente_Operis/agente_operis/` usa el motor `reglas`
> (gratis, determinista) por defecto — son dos carpetas independientes con el
> mismo código; asegúrate de estar en la que quieres antes de ejecutar
> `python main.py`. Rellena `GROQ_API_KEY` en el `.env` de esta carpeta
> (nunca en `.env.example`) para que el motor `llm` funcione.

Proyecto: **Mitümi — arquitectura de agentes de The Bridge (bootcamp DS)**
Tipo de componente: **Agente dependiente del orquestador, ejecutable localmente**
Estructura base: **alineada con el precedente real `Agente_04_Copilot_Raul/lumen_agente_04/`**

**Conexión con el orquestador y la base de datos:** el orquestador invoca a este agente llamando a `ejecutar_agente(payload)` desde `src/agente.py` (mismo contrato que el resto de agentes del proyecto); con la base de datos, `agente_operis` **no se conecta directamente** — nunca lee ni escribe en ella — sino que reutiliza los nombres de columna reales de `Datos_alimentación_bbdd_Leire_Eduardo/*.csv` en su JSON de salida, para que una persona (o el propio orquestador) pueda volcar la propuesta ya validada con un `INSERT` directo. **Excepción explícita:** las fechas (`evento.fecha_inicio`, `evento.fecha_fin`, `presupuesto.fecha`) se devuelven en `DD/MM/AAAA` (decisión del cliente, para que se lean directamente), no en el `AAAA-MM-DD` que usan esas columnas en los CSV — el backend/orquestador debe reconvertirlas a ISO antes de cualquier `INSERT` real (ver sección 11).

---

## 0. Principio arquitectónico

`agente_operis` se desarrolla como subproyecto propio, ejecutable en local para pruebas:

```bash
cd agente_operis
python main.py --demo
```

En la arquitectura final no actúa de forma autónoma. Lo llama el **agente orquestador** de Mitümi
mediante la interfaz común `ejecutar_agente(payload)`:

```text
Backend / Orquestador
        ↓
ejecutar_agente(payload)
        ↓
agente_operis (autocompletado de briefings)
        ↓
Respuesta estructurada (propuesta, nunca escritura directa)
        ↓
[PERSONA revisa y confirma] → Orquestador / Backend → BD
```

`agente_operis` es un agente **de propuesta**, no de acción: lee un documento y propone un JSON
estructurado. Nunca guarda, nunca decide, nunca escribe en la base de datos.

---

## 1. Regla crítica no modificable

La estructura interna puede adaptarse, **excepto la comunicación con el orquestador**:

```text
agente_operis/src/agente.py
```

Debe exponer siempre:

```python
def ejecutar_agente(payload: dict) -> dict:
    """
    Punto de entrada común de agente_operis.
    Lo usa main.py (local), el orquestador o una futura API.
    """
    ...
```

Y respetar siempre (regla de oro, compartida con `Documentacion_agentes/Agente_OPERIS.md`):

```text
1. Mismo contrato de entrada.
2. Mismo contrato de salida.
3. Salida siempre estructurada.
4. agente_operis no invoca directamente a otro agente.
5. agente_operis no escribe directamente en la BBDD final — no escribe nunca, bajo ningún modo.
6. agente_operis no ejecuta acciones externas reales (no envía nada, no confirma nada).
7. requiere_validacion_humana es SIEMPRE True — toda propuesta pasa por revisión de una persona.
```

En una integración final dentro del monorepo de Mitümi, esta carpeta se ubicaría en
`src/agents/agente_operis/`; aquí se entrega como carpeta autocontenida `agente_operis/` para poder
probarla de forma aislada — mismo criterio que `lumen_agente_04/`.

---

## 2. Identificación del agente

| Campo | Valor |
|---|---|
| **Nombre del agente** | `agente_operis` |
| **Equipo responsable** | Ainara, David |
| **Fase del evento que cubre** | Captación inicial — autocompletado del briefing antes de crear el evento en el sistema |
| **Propósito en una frase** | Leer un briefing de evento (.txt/.pdf/.docx) y proponer un JSON estructurado por bloque (Evento, Cliente, Espacio, Sala, Presupuesto, Ponentes), listo para revisión humana. |
| **Tipo de agente** | Dependiente del orquestador, human-in-the-loop, no autónomo |
| **Modo por defecto** | `propuesta` (nunca escribe; no aplica `ejecucion_controlada`) |
| **Estado** | Beta — motor de reglas probado end-to-end; motor LLM integrado, pendiente de primera prueba con clave real de Groq |
| **Última actualización** | 09/07/2026 |

---

## 3. Qué hace este agente

```text
Se le pasa el texto de un briefing (email de un cliente, documento adjunto, etc.) y devuelve una
propuesta de los 6 bloques de datos del evento, marcando qué campos obligatorios se han detectado y
cuáles faltan, para que una persona los revise y confirme antes de guardar nada.
```

### Capacidades principales

- Extrae campos estructurados de un briefing en texto libre, agrupados en 6 bloques que reflejan las
  tablas reales de la base de datos (`eventos`, `clientes`, `espacios`, `salas`, `presupuestos`,
  `ponentes`).
- **Dos motores intercambiables, mismo esquema de salida:**
  - `reglas` (por defecto, gratis, determinista): regex + etiquetas explícitas del documento.
  - `llm` (Groq, `openai/gpt-oss-120b`): interpretación de texto libre para los matices que el motor
    de reglas no cubre.
- Prioriza siempre las etiquetas explícitas del documento (`"Cliente: TechCorp S.L."`) sobre cualquier
  heurístico de texto libre.
- Calcula qué pestañas se han cumplimentado y qué campos obligatorios del evento faltan
  (`_validacion.porcentaje_completado`, sobre `CAMPOS_OBLIGATORIOS_EVENTO`).

### Ejemplo de uso

Ver `inputs/payload_demo.json` para un caso real completo (email de un cliente solicitando la
organización de un congreso). Resultado esperado en `outputs/respuestas_json/salida_demo.json`.

---

## 4. Qué NO hace este agente

`agente_operis` **no debe**:

- escribir directamente en la base de datos final (ni en ningún modo);
- enviar emails ni mensajes reales;
- confirmar reservas de espacios ni aprobar presupuestos;
- decidir el estado definitivo de un evento — solo propone un valor de texto si el documento lo
  etiqueta explícitamente;
- inventar ni deducir datos que no estén explícitos en el texto (campo no encontrado → `""`, nunca
  una suposición);
- invocar directamente a otros agentes;
- sustituir al orquestador ni al backend;
- leer bandejas de correo directamente — recibe texto ya extraído de un documento; la ingesta directa
  de un buzón de email se valoró y **se descartó** para esta iteración (ver
  `docs/Agente_OPERIS_implementacion.md`, sección 14).

Límites de esquema conocidos (no son bugs, están documentados):

- con varios ponentes a la vez, si un dato suelto (teléfono, email) no está etiquetado a un ponente
  concreto, no se asigna — se deja para revisión manual;
- el bloque `espacio` es un único objeto, no una lista: si el briefing compara varias sedes, solo una
  queda estructurada y el resto quedan resumidas en `espacio.nota`;
- el estado del evento (`evento.estado`) solo se detecta si el documento lo etiqueta explícitamente
  (nunca por heurístico de texto libre) — evita confundirlo con el estado del presupuesto, que suele
  usar vocabulario parecido ("pendiente de aprobación").

---

## 5–7. Estructura del agente

Árbol real de `agente_operis/` (verificado sobre el disco; se omiten los `__pycache__/` que genera
Python automáticamente al ejecutar):

```text
agente_operis/
│
├── README.md                  ← este archivo
├── main.py                    ← consola: --demo = un solo disparo sobre inputs/payload_demo.json
│                                  (regresión/prueba reproducible); ruta a archivo = procesa un
│                                  briefing cualquiera (.txt/.pdf/.docx)
├── requirements.txt            ← sin dependencias obligatorias (motor de reglas = librería estándar);
│                                  groq/pypdf/python-docx/tiktoken son opcionales
├── .env.example                ← plantilla sin secretos
├── .gitignore                  ← .env, __pycache__/, *.pyc
│
├── config/
│   ├── __init__.py
│   ├── settings.py            ← carga variables desde .env (sin dependencias externas)
│   └── permisos.py            ← fuerza ALLOW_DB_WRITE=False (y el resto) de forma no configurable
│
├── prompts/
│   └── prompt_sistema.md      ← rol, esquema de salida y regla de "no inventar" para el motor LLM
│
├── src/
│   ├── __init__.py
│   ├── agente.py               ← punto de entrada OBLIGATORIO: ejecutar_agente(payload).
│   │                               Reexporta la lógica real desde nucleo.py (no tocar más allá).
│   ├── nucleo.py               ← lógica real: valida entrada, elige motor, construye la salida común
│   ├── schemas.py               ← contrato de salida (construir_salida_base) + esquema de los 6
│   │                               bloques de datos (crear_estructura_vacia_completa) + cálculo de
│   │                               % completado (generar_aviso_y_validacion)
│   ├── validaciones.py          ← validar_entrada(payload) contra el contrato común de entrada
│   ├── funciones.py             ← motor de reglas (regex + etiquetas explícitas del documento)
│   ├── llm.py                   ← motor LLM (Groq, openai/gpt-oss-120b) — mismo esquema de salida
│   │                               que funciones.py, intercambiables desde nucleo.py
│   └── rag.py                   ← stub, no aplica a este agente (no consulta histórico ni BD)
│
├── inputs/
│   └── payload_demo.json       ← payload de ejemplo que usa main.py --demo
│
├── data/
│   ├── conocimiento/            ← diccionarios de conocimiento del motor de reglas
│   │   ├── field_aliases_3.py   ← etiquetas explícitas reconocidas por campo ("Cliente:", "Aforo:"...)
│   │   ├── cities_3.py          ← ciudades reconocidas
│   │   ├── event_types_3.py     ← tipos de evento reconocidos
│   │   └── status_3.py          ← BUDGET_STATUS / EVENT_STATUS, verificados contra las columnas
│   │                               reales de Datos_alimentación_bbdd_Leire_Eduardo/*.csv
│   └── ejemplos/
│       ├── briefing_prueba.txt     ← caso simple (un cliente, un espacio, sin ponentes)
│       └── briefing_complejo.txt   ← caso complejo (varios espacios candidatos, varios ponentes)
│
├── docs/
│   ├── Agente_OPERIS_implementacion.md  ← ficha de documentación (copia de Documentacion_agentes/)
│   ├── estimacion_tokens.py             ← genera ESTIMACION_TOKENS.md a partir de los dos ejemplos
│   └── ESTIMACION_TOKENS.md             ← informe de coste/tokens del motor LLM (caso simple y complejo)
│
└── outputs/
    └── respuestas_json/
        └── salida_demo.json    ← aquí guarda main.py --demo la salida de cada ejecución
```

Nota importante sobre `src/agente.py`: el nombre de archivo y la función `ejecutar_agente(payload)`
son el contrato obligatorio del proyecto (sección 1) y no cambian. La lógica en sí vive en
`src/nucleo.py` para mantener el fichero de contrato lo más simple y estable posible; `agente.py`
solo hace `from src.nucleo import ejecutar_agente`.

---

## 8. Archivo `.env`

Ver `.env.example` para la plantilla completa (sin secretos). Variables clave:

```env
OPERIS_MOTOR=reglas                     # "reglas" (gratis, por defecto) o "llm" (Groq)
GROQ_API_KEY=                           # solo en .env real, nunca en .env.example ni en el código
GROQ_MODEL=openai/gpt-oss-120b
```

`.gitignore` incluye `.env`, `__pycache__/`, `*.pyc`. La API key vive solo en `.env` (nunca en
`.env.example`, nunca hardcodeada en `src/llm.py`).

Permisos, fijados en código en `config/permisos.py` (no configurables al alza desde `.env`):

```python
ALLOW_DB_WRITE = False
ALLOW_EXTERNAL_SEND = False
ALLOW_CREATE_EVENT = False
ALLOW_AUTO_APPROVAL = False
```

---

## 9. Contrato de entrada

`src/validaciones.py` exige la presencia de: `tipo_peticion`, `origen`, `usuario_solicitante`,
`rol_usuario`, `datos`, `contexto`, `modo`, y también la clave `id_evento` (aunque su valor puede ser
`null` — a diferencia de un agente que actúa sobre un evento ya existente, `agente_operis` propone los
datos de un evento que **todavía no existe** en la BD).

Dentro de `datos`:

- `datos.texto_briefing` (obligatorio): texto ya extraído del documento a analizar.
- `datos.motor` (opcional, por defecto `config.settings.MOTOR_POR_DEFECTO`): `"reglas"` o `"llm"`.

```json
{
  "id_evento": null,
  "id_registro": null,
  "tipo_peticion": "extraer_briefing",
  "origen": "manual",
  "usuario_solicitante": "cli",
  "rol_usuario": "organizador",
  "datos": {
    "texto_briefing": "...",
    "motor": "reglas"
  },
  "contexto": {},
  "modo": "propuesta"
}
```

Ver `inputs/payload_demo.json` para el payload real que usa `main.py --demo`.

---

## 10. Contrato de salida

```json
{
  "ok": true,
  "agente": "agente_operis",
  "tipo_peticion": "extraer_briefing",
  "resumen": "Se ha cumplimentado información en las pestañas Evento, Cliente y Presupuesto. Requiere validación.",
  "datos_detectados": {
    "evento": { "...": "..." },
    "cliente": { "...": "..." },
    "espacio": { "...": "..." },
    "sala": { "...": "..." },
    "presupuesto": { "...": "..." },
    "ponentes": []
  },
  "acciones_propuestas": [],
  "bloqueos_detectados": ["fecha_fin"],
  "borradores_generados": [],
  "requiere_validacion_humana": true,
  "nivel_riesgo": "bajo",
  "errores": [],
  "trazas": {
    "fuentes_consultadas": ["motor:reglas"],
    "timestamp": "2026-07-09T08:30:23",
    "modo": "propuesta"
  }
}
```

`requiere_validacion_humana` es **siempre `true`** y `nivel_riesgo` es **siempre `"bajo"`** en
`agente_operis` — el agente nunca escribe ni envía nada en ningún modo, así que no hay escenario de
riesgo alto (`src/schemas.py` lo fija en código, no solo por diseño de prompt).
`acciones_propuestas` y `borradores_generados` quedan siempre vacíos, por el mismo motivo.

---

## 11. Los 6 bloques de datos (`datos_detectados`)

Mismos nombres de bloque y de campo que las columnas reales de la BD
(`Datos_alimentación_bbdd_Leire_Eduardo/*.csv`), ver `src/schemas.py::crear_estructura_vacia_completa`:

```text
evento:      nombre_evento, ciudad, lugar_confirmado, fecha_inicio, fecha_fin,
             numero_personas, tipo_evento, estado, nota
cliente:     cliente, empresa, email, telefono, sector, ciudad
espacio:     nombre_espacio, ciudad, direccion, capacidad_total, aforo, nota,
             telefono_contacto, nombre_contacto, email_contacto
sala:        nombre_sala, tipo, capacidad_max_sala, nota_sala
presupuesto: estado_presupuesto, total, fecha, nota_ubicacion, precio_ubicacion,
             precio_catering, precio_audiovisuales, precio_otros, nota_catering,
             nota_audiovisuales, nota_otros, observaciones
ponentes:    [lista] nombre_ponente, doc_identificacion, email, sector, telefono,
             foto_link, cv_link, empresa, cargo, nombre_hotel, nota_transporte,
             horario_ida_transporte, horario_vuelta_transporte, localizacion_hotel,
             horario_ponencia, checking_horario, ponente_estado, presentacion_link,
             billete_ida_link, billete_vuelta_link, tipo_ponencias
```

`estado_presupuesto` solo admite los valores reales de `presupuestos.csv` (`"Aprobado"` /
`"Pendiente"`) — ver `data/conocimiento/status_3.py`. Campos obligatorios del evento, sobre los que se
calcula `_validacion.porcentaje_completado`: `nombre_evento`, `ciudad`, `fecha_inicio`, `fecha_fin`,
`numero_personas`, `tipo_evento`.

**Formato de fecha — decisión del cliente:** `evento.fecha_inicio`, `evento.fecha_fin` y
`presupuesto.fecha` se devuelven en `DD/MM/AAAA` (p. ej. `"15/10/2026"`), no en el `AAAA-MM-DD` que
usan esas mismas columnas en `eventos.csv`/`presupuestos.csv`. Internamente, los dos motores
(`reglas` y `llm`) siguen trabajando en ISO — es el formato más fiable para parsear y para que el LLM
no confunda día/mes — y la conversión final a `DD/MM/AAAA` se hace en un único punto compartido por
ambos motores: `src/schemas.py::generar_aviso_y_validacion` (ver `_fecha_iso_a_visible`). El
backend/orquestador debe reconvertir estos tres campos a ISO antes de cualquier `INSERT` real.

---

## 12. Flujo interno implementado

```text
1. main.py (o el orquestador) construye el payload y llama a ejecutar_agente(payload) (src/agente.py).
2. src/validaciones.py valida el contrato de entrada mínimo.
3. src/nucleo.py elige el motor (datos.motor, o config.settings.MOTOR_POR_DEFECTO si no se indica):
   - "reglas" -> src/funciones.py: regex + etiquetas explícitas (data/conocimiento/), determinista.
   - "llm"    -> src/llm.py: llama a Groq (openai/gpt-oss-120b), temperature=0, JSON forzado,
                 usando el prompt de prompts/prompt_sistema.md. Si el paquete `groq` no está
                 instalado o falta GROQ_API_KEY, falla de forma controlada (nunca "adivina").
4. Ambos motores devuelven el mismo esquema (los 6 bloques) y pasan por
   src/schemas.py::generar_aviso_y_validacion, que calcula qué pestañas se han cumplimentado y el
   % de campos obligatorios detectados — mismo criterio para los dos motores.
5. src/nucleo.py construye la salida común (src/schemas.py::construir_salida_base), fija
   requiere_validacion_humana=true y registra la fuente usada en trazas.fuentes_consultadas.
6. main.py imprime el resultado y, en modo --demo, lo guarda en outputs/respuestas_json/salida_demo.json.
```

A diferencia de `lumen_agente_04` (que consulta datos ya existentes en la BD), `agente_operis` nunca
lee la base de datos: `src/rag.py` es un stub explícito por ese motivo (ver su docstring).

---

## 13. Prompts

```text
prompts/
└── prompt_sistema.md   ← rol, regla de "nunca inventar", y el esquema de salida (ESQUEMA_SALIDA de
                            src/llm.py, insertado en runtime vía construir_prompt_sistema())
```

---

## 14. Datos e integraciones

```text
data/conocimiento/*.py   ← diccionarios de conocimiento del motor de reglas (etiquetas, ciudades,
                             tipos de evento, estados) — fuente única de verdad del motor "reglas"
data/ejemplos/*.txt      ← los dos briefings de ejemplo (simple y complejo) usados por
                             docs/estimacion_tokens.py y para pruebas manuales
```

No hay integración de lectura ni escritura con la base de datos real: `agente_operis` solo reutiliza
los nombres de columna de `Datos_alimentación_bbdd_Leire_Eduardo/*.csv` para que su propuesta sea
compatible con un `INSERT` posterior, hecho por el backend/orquestador tras la validación humana.

---

## 15. Modo seguro por defecto

```python
ALLOW_DB_WRITE = False          # fijo en config/permisos.py, no configurable
ALLOW_EXTERNAL_SEND = False
ALLOW_CREATE_EVENT = False
ALLOW_AUTO_APPROVAL = False
```

En `agente_operis` estos flags no son un "modo por defecto que se podría cambiar más adelante": son
una restricción arquitectónica permanente, reforzada en `config/permisos.py`.

---

## 16. Ejecución local

```bash
cd agente_operis
pip install -r requirements.txt   # opcional: sin dependencias para el motor de reglas
cp .env.example .env              # opcional: solo necesario para el motor llm
python main.py --demo
```

`python main.py --demo`: un solo disparo sobre `inputs/payload_demo.json` (motor `reglas`, gratis).
Imprime la respuesta, la compara con `outputs/respuestas_json/salida_demo.json` (ignorando
`trazas.timestamp`, que cambia en cada ejecución por diseño) y confirma si el resultado es
determinista, y la vuelve a guardar.

```bash
python main.py ruta/al/briefing.txt              # motor "reglas" (por defecto)
python main.py ruta/al/briefing.txt --motor llm  # motor LLM (Groq, requiere GROQ_API_KEY en .env)
```

`python docs/estimacion_tokens.py` (desde `agente_operis/`, requiere `pip install tiktoken`):
regenera `docs/ESTIMACION_TOKENS.md` con la estimación de coste/tokens del motor LLM para el caso
simple y el caso complejo.

---

## 17. Casos de fallo específicos de `agente_operis`

| Fallo | Comportamiento esperado |
|---|---|
| PDF escaneado sin capa de texto | Formulario en blanco pese a documento con contenido — límite conocido, no hay OCR |
| Varios ponentes mencionados a la vez, datos sueltos sin etiqueta | No se asignan automáticamente esos datos sueltos; revisión manual |
| Varios espacios candidatos a comparar | Solo uno queda estructurado en `espacio`; el resto, resumido en `espacio.nota` |
| Estado de evento/presupuesto con vocabulario ambiguo | Solo se rellena si el documento lo etiqueta explícitamente — nunca por heurístico de texto libre |
| Motor `llm` sin `GROQ_API_KEY` o sin el paquete `groq` instalado | Error controlado (`ImportError`/`ValueError`); el motor `reglas` sigue disponible sin ninguna dependencia |
| El LLM devuelve un JSON inválido | Error controlado (`ValueError`), nunca se "adivina" un JSON mal formado |
| Free tier de Groq agotado (200.000 tokens/día para este modelo) | Se detiene la extracción vía `llm`; usar el motor `reglas` (sin coste) o esperar al día siguiente |

---

## 18. Checklist final

- [x] Existe `README.md` (este archivo).
- [x] Existe `.env.example` sin secretos.
- [x] Existe `main.py` para ejecución local — funciona out-of-the-box en modo `--demo` (motor `reglas`).
- [x] Existe `src/agente.py` con `ejecutar_agente(payload)` (reexporta `src/nucleo.py`).
- [x] Existe `src/schemas.py` y `src/validaciones.py` con el contrato de entrada/salida común.
- [x] Existe `prompts/prompt_sistema.md`, y se usa de verdad (`src/llm.py` lo carga en runtime).
- [x] Existe `inputs/payload_demo.json` y `outputs/respuestas_json/salida_demo.json` (regresión
      determinista verificada: mismo texto → misma salida, motor `reglas`).
- [x] El agente no invoca a otros agentes.
- [x] El agente no escribe directamente en la BD final (restricción de diseño, no solo de `.env`).
- [x] El agente no envía emails/mensajes reales.
- [x] Los permisos por defecto están en modo seguro (y son fijos, no solo por defecto).
- [x] Se documenta qué hace y qué no hace (secciones 3-4).
- [x] Motor de reglas probado end-to-end (`python main.py --demo`, con y sin campos obligatorios).
- [x] Motor LLM integrado (Groq, `openai/gpt-oss-120b`) con estimación de coste/tokens documentada
      (`docs/ESTIMACION_TOKENS.md`), casos de fallo controlados (sin clave, JSON inválido).
- [ ] Pendiente: primera prueba real del motor LLM con una clave de Groq activa (hasta ahora solo
      verificado que la petición se construye correctamente).
- [ ] Pendiente: conectar una interfaz de revisión humana (Streamlit u otra) — los prototipos
      actuales del proyecto usan una versión anterior y más simple del motor de reglas.
- [ ] Pendiente: integrar con el orquestador real cuando exista (hoy ya expone el contrato
      `ejecutar_agente(payload)` que ese orquestador necesitaría).
- [ ] Pendiente (mejora de esquema, no bloqueante): modelar `espacio` como lista, igual que
      `ponentes`, si comparar varios espacios candidatos resulta ser un caso de uso habitual.

## Nota sobre las pruebas de este entregable

El motor de reglas se ha probado de extremo a extremo con `python main.py --demo` (determinista,
verificado con `briefing_prueba.txt`) y con `briefing_complejo.txt` (varios ponentes y espacios
candidatos). El motor LLM se ha probado hasta el punto de construir correctamente la petición
(prompt de sistema + esquema + texto); la llamada real a la API de Groq no se ha podido verificar
en este entorno de generación por no disponer de una clave activa — en un equipo con clave real de
`console.groq.com`, debería funcionar tal cual (ver `docs/ESTIMACION_TOKENS.md` para el coste
esperado).
