**Conexión con el orquestador y la base de datos:** el orquestador invoca a este agente llamando a `ejecutar_agente(payload)` desde `src/agente.py` (mismo contrato que el resto de agentes del proyecto); con la base de datos, `agente_operis` **no se conecta directamente** — nunca lee ni escribe en ella — sino que reutiliza los nombres de columna reales de `Datos_alimentación_bbdd_Leire_Eduardo/*.csv` en su JSON de salida, para que una persona (o el propio orquestador) pueda volcar la propuesta ya validada con un `INSERT` directo. **Excepción explícita:** las fechas (`evento.fecha_inicio`, `evento.fecha_fin`, `presupuesto.fecha`) se devuelven en `DD/MM/AAAA` (decisión del cliente), no en el `AAAA-MM-DD` que usan esas columnas en los CSV — el backend/orquestador debe reconvertirlas a ISO antes de cualquier `INSERT` real.

---

# Documentación del Agente: `agente_operis` (implementación real)

> **Versión de la documentación:** 1.2.0
> **Última actualización:** 09/07/2026
> **Autor / Equipo responsable:** Ainara / David — Data Science, The Bridge
> **Estado:** 🟡 Beta *(motor de reglas probado; motor LLM integrado, pendiente de primera prueba con clave real)*

---

## Nota importante

Este documento es el complemento de `Agente_OPERIS.md` (que describe la arquitectura **objetivo/aspiracional** del agente: backend Node, Groq/Llama, Prisma, canal Telegram). Este documento describe, con la misma honestidad, **lo que existe hoy y funciona**: una implementación en Python, con dos motores de extracción intercambiables, siguiendo la estructura de "agente dependiente" definida por `Definicion_Agentes_RAUL/`, alineada con el precedente real `Agente_04_Copilot_Raul/lumen_agente_04/`.

Documentación técnica completa (código, contratos, casos de prueba) en el propio código: [`README.md`](../README.md), en la raíz de esta misma carpeta del agente. Este documento es la versión "para todo el equipo", sin necesidad de leer código.

**Regla de oro (compartida con `Agente_OPERIS.md`):** el agente **nunca escribe en la base de datos** ni inventa datos que no estén explícitos en el documento. Solo propone; una persona revisa y confirma.

---

## 1. Resumen ejecutivo

| Campo | Descripción |
|---|---|
| **Nombre del agente** | `agente_operis` — Autocompletado de briefings de eventos |
| **Propósito en una frase** | Lee un briefing de evento (.txt, .pdf o .docx) y propone un JSON estructurado, clasificado por bloque (Evento, Cliente, Espacio, Sala, Presupuesto, Ponentes), listo para revisión humana. |
| **Modelo(s) LLM utilizado(s)** | `openai/gpt-oss-120b` en Groq (motor `llm`, opcional). El motor `reglas` (por defecto, gratis) no usa ningún LLM — extracción por regex y etiquetas explícitas del documento. |
| **Tipo de agente** | Automatización de extracción de datos, dependiente de orquestador (human-in-the-loop, no autónomo). |
| **Entorno de ejecución** | Local / dependiente del backend que lo invoque. Sin servicio propio desplegado. |
| **Frameworks / SDK** | Python estándar (motor de reglas). SDK `groq` (motor LLM, opcional, mismo SDK que usa `agente_alerta_roberto`/Vigil). |
| **Nivel de criticidad** | Bajo — el peor fallo posible es un formulario mal cumplimentado que la persona corrige antes de confirmar. No hay escritura autónoma en BD. |

> **En lenguaje llano:** igual que describe `Agente_OPERIS.md`, es como un becario rápido: le pasas el briefing de un evento y él propone los datos del formulario. Hoy, ese becario puede trabajar de dos formas — con una lista de reglas fijas (gratis, siempre igual) o preguntándole a un modelo de lenguaje (Groq, con un coste mínimo) — pero en ambos casos nunca guarda nada por su cuenta.

---

## 2. Propósito y límites del agente

### 2.1 Su cometido
- [x] **Extrae campos estructurados de un briefing en texto libre**, agrupados en 6 bloques que reflejan las tablas reales de la base de datos (`eventos`, `clientes`, `espacios`, `salas`, `presupuestos`, `ponentes`). Caso de uso: pegar el email de un cliente y obtener nombre del evento, fechas, ciudad, aforo, presupuesto y ponentes ya propuestos.
- [x] **Dos motores intercambiables, mismo esquema de salida**: `reglas` (regex + etiquetas, gratis, determinista) y `llm` (Groq, con matices de interpretación de texto libre que el motor de reglas no cubre).
- [x] **Prioriza las etiquetas explícitas del documento** ("Cliente: Michelin") sobre cualquier heurístico de texto libre.
- [x] **Marca por bloque qué se ha cumplimentado** y qué campos obligatorios faltan, para que la revisión humana se concentre ahí.

### 2.2 Qué NO hace (límites explícitos)
- [x] **No escribe en la base de datos.** Solo devuelve un diccionario/JSON de propuesta.
- [x] **No inventa ni deduce datos.** Lo que no aparece explícito en el texto se queda vacío (`""`).
- [x] **No hace OCR en PDFs escaneados** — depende de que el documento tenga capa de texto.
- [x] **No resuelve la asignación de datos individuales de ponente cuando hay varios ponentes a la vez** — con un único ponente detectado sí lo hace sin ambigüedad.
- [x] **No modela varios espacios candidatos en comparación** — el bloque `espacio` es un único objeto, no una lista; si el briefing compara varias sedes, solo una queda como propuesta estructurada y el resto quedan resumidas como texto libre.
- [x] **No lee directamente bandejas de correo.** Recibe texto ya extraído de un documento — la ingesta de un buzón de email se valoró y se descartó por ahora (ver sección 14).

### 2.3 Casos de uso fuera del alcance de `agente_operis`
- Cumplimentar automáticamente y guardar sin revisión humana (viola la regla de oro).
- Cruzar o deducir datos entre varios documentos para completar campos ausentes.
- Coordinar con otros agentes (ponentes, presupuesto, comunicación) — eso corresponde a un futuro orquestador, no a este agente.
- Decidir el estado definitivo de un evento o presupuesto en la BD — solo propone un valor de texto, la decisión y el guardado son de la persona/backend.

---

## 3. Inicio rápido (Quick Start)

### 3.1 Requisitos previos
```
- Python 3.10+
- (Opcional, motor llm) paquete `groq` + clave gratuita de console.groq.com
- (Opcional, PDF) PyPDF2 o pypdf
- (Opcional, DOCX) python-docx
```

### 3.2 Instalación / configuración
```bash
cd agente_operis
pip install -r requirements.txt
cp .env.example .env
```

### 3.3 Ejemplo realista de uso
```text
Input del usuario:
Un briefing en texto libre, p. ej.:
"Se trata del Congreso Anual de Innovación Digital, en Madrid, del 15
al 17 de octubre de 2026. Aforo de 350 personas. Presupuesto de 45.000
euros, pendiente de aprobación interna. Cliente: TechCorp S.L."

Proceso interno esperado:
1. Se construye el payload común (id_evento=null, datos.texto_briefing=...).
2. ejecutar_agente(payload) valida el contrato y elige el motor (reglas por defecto).
3. El motor extrae los 6 bloques de datos.
4. Se calcula qué campos obligatorios faltan y qué pestañas se han rellenado.
5. Se devuelve la respuesta estructurada, con requiere_validacion_humana=true.

Output esperado:
{
  "ok": true,
  "agente": "agente_operis",
  "resumen": "Se ha cumplimentado información en las pestañas Evento, Cliente y Presupuesto. Requiere validación.",
  "datos_detectados": { "evento": {...}, "cliente": {...}, "presupuesto": {...}, ... },
  "bloqueos_detectados": [],
  "requiere_validacion_humana": true
}
```

---

## 4. Lógica de decisión

Al igual que la versión objetivo descrita en `Agente_OPERIS.md`, este agente es deliberadamente **sencillo y de un solo paso** (sin bucle de razonamiento tipo ReAct). La única "decisión" no trivial es qué motor usar y con qué prioridad tratar cada fuente de información.

### 4.1 Entradas que afectan a las decisiones
| Entrada | Afecta a | Ejemplo |
|---|---|---|
| Texto del briefing | Todo el resultado | El documento pegado o subido |
| Motor elegido (`reglas`/`llm`) | Cómo se interpreta el texto | `reglas` no entiende sinónimos no listados; `llm` sí puede generalizar |
| Etiquetas explícitas en el texto | Prioridad máxima sobre cualquier heurístico | `"Cliente: Michelin"` |
| Esquema de la BD (nombres de columna reales) | Estructura de la salida | CSV de `Datos_alimentación_bbdd_Leire_Eduardo/` |

### 4.2 Priorización de acciones
```
1 · Etiqueta explícita del documento (máxima fiabilidad — es texto literal)
2 · Heurístico de texto libre / interpretación del LLM
3 · Campo vacío (nunca se inventa un valor)
```

### 4.3 Capa de percepción
Antes de razonar, el documento (`.pdf`/`.docx`/`.txt`) se convierte a texto plano. La calidad de esa conversión determina el techo de la extracción — un PDF escaneado como imagen, sin capa de texto, llega casi vacío en ambos motores.

### 4.4 Mecanismos de fallback
- **Campo no encontrado** → `""`, nunca se inventa (igual que exige `Agente_OPERIS.md` para la versión con LLM).
- **Motor LLM sin clave configurada** → error controlado; el motor `reglas` sigue funcionando sin ninguna dependencia externa.
- **JSON inválido del LLM** → error controlado, nunca se "adivina" un JSON mal formado.
- **Varios ponentes o varios espacios candidatos a la vez** → ambigüedad no resuelta automáticamente; se deja para revisión manual (ver sección 5).

---

## 5. Modos de fallo

| Patrón de fallo | Síntoma observable | Causa probable | Posible corrección |
|---|---|---|---|
| PDF vacío | Formulario en blanco pese a documento con contenido | PDF escaneado (imagen), sin capa de texto | Pedir documento editable o alta manual |
| Ponente sin datos individuales | Email/teléfono/empresa vacíos por ponente | Varios ponentes mencionados a la vez: no hay forma fiable de saber a cuál corresponde cada dato suelto | Revisión manual; con un único ponente sí se asigna automáticamente |
| Campo cruzado entre entidades | Un dato de una entidad (p. ej. email de un ponente) aparece también en otra (cliente) | Heurístico de texto libre sin contexto de a quién pertenece el dato | Mitigado para varios campos concretos (email/teléfono de cliente, estado del evento); no cubre todos los casos posibles |
| Espacios candidatos mal representados | Solo se recoge un espacio pese a que el texto compara varios | El esquema de datos modela un único espacio, no una lista | Revisión manual; ampliar el esquema si este caso se vuelve habitual |
| Estado (evento/presupuesto) no detectado | El campo de estado queda vacío pese a mencionarse | El texto usa una expresión distinta a los valores cerrados conocidos | Revisión manual; ampliar la lista de sinónimos conocidos |
| Motor LLM: coste o límite gratuito agotado | Se detiene la extracción vía `llm` | Groq limita el free tier a 200.000 tokens/día para este modelo | Usar el motor `reglas` (sin coste), o esperar al día siguiente |

---

## 6. Observabilidad

No hay logging estructurado ni trazas persistidas todavía — el agente es lo bastante simple como para depurar leyendo la respuesta completa, que siempre incluye el detalle del error si algo falla. Pendiente para cuando se integre con un backend/orquestador real.

---

## 7. Comportamiento determinista vs. no determinista

| Componente | Determinista | No determinista | Notas |
|---|---|---|---|
| Lectura de archivo | ✅ | | |
| Motor de reglas | ✅ | | Mismo texto → misma salida, siempre — verificado con una prueba de regresión local |
| Motor LLM | | ✅ | `temperature=0` acota la variabilidad, no la elimina del todo |
| Validación y cálculo de campos pendientes | ✅ | | |

A diferencia de la versión objetivo (`Agente_OPERIS.md`), que asume que la única vía es un LLM, esta implementación real ofrece un motor 100% determinista como opción por defecto — relevante para pruebas y para no depender de un proveedor externo salvo que se elija explícitamente.

---

## 8. Patrones de integración

### 8.1 Arquitectura general
```
Documento (.txt/.pdf/.docx) → texto plano
        → motor "reglas" (gratis) o motor "llm" (Groq)
        → JSON estructurado (6 bloques) + % completado
        → [PERSONA revisa y confirma] → backend → BD
```
El agente **no es un servicio aparte**: se invoca como una función Python (`ejecutar_agente(payload)`) desde quien lo use — hoy, scripts de prueba locales; en el futuro, el orquestador del proyecto.

### 8.2 Handoff a supervisión humana
- **Condición de handoff:** siempre. Toda propuesta pasa por revisión humana antes de guardarse — la respuesta del agente lo marca explícitamente (`requiere_validacion_humana: true`).
- **Interfaz:** todavía no hay una interfaz visual conectada a esta implementación (los prototipos de Streamlit del proyecto usan una versión anterior y más simple del motor de reglas, sin el motor LLM ni el contrato de orquestador). Sería el siguiente paso natural.

### 8.3 Gestión de estado entre ejecuciones
Sin estado ni memoria entre documentos — cada extracción es independiente (mismo principio que documenta `Agente_OPERIS.md`, sección 8.4).

---

## 9. Herramientas y permisos (Tools / Function calling)

| Herramienta | Descripción | Permisos requeridos | Riesgo si falla |
|---|---|---|---|
| Lectura de archivo | Convierte .txt/.pdf/.docx a texto plano | Lectura de archivo local | Bajo — texto vacío o parcial, detectable en revisión |
| Motor de reglas | Extracción determinista por regex/etiquetas | Ninguno (sin red) | Bajo |
| Motor LLM (Groq) | Llamada a la API de Groq, `temperature=0`, salida JSON forzada | Ejecución (llamada externa) | Bajo — propuesta errónea, corregible por la persona |

---

## 10. Seguridad y cumplimiento

- **Datos sensibles procesados:** PII de contacto (nombres, emails, teléfonos de clientes y ponentes; documento de identidad de ponentes si el briefing lo incluye).
- **Prompt injection / mitigaciones:** en el motor LLM, el texto del documento se separa del prompt de sistema (que fija las reglas y el esquema); el modelo se instruye para devolver solo JSON con claves fijas.
- **Límites de acción destructiva:** ninguna — el agente no escribe en BD ni envía nada externamente en ninguno de los dos motores.
- **Gestión de credenciales:** `GROQ_API_KEY` vía variable de entorno / `.env` (no versionado), nunca hardcodeada — mismo patrón que ya usa `agente_alerta_roberto`/Vigil en este proyecto.
- **Cumplimiento normativo aplicable:** RGPD (datos de contacto de clientes y ponentes).

---

## 11. Evaluación y monitoreo

### 11.1 Métricas clave
| Métrica | Objetivo | Frecuencia de revisión |
|---|---|---|
| Tasa de éxito de extracción (campos obligatorios) | *[por fijar tras uso real]* | — |
| Coste por llamada del motor LLM | ~$0.0004–$0.001/llamada (ver detalle abajo) | — |

**Detalle de coste (motor LLM, referencia julio 2026):** `openai/gpt-oss-120b` en Groq, $0.15/1M tokens de entrada, $0.60/1M de salida. Un briefing simple cuesta ≈$0.0004/llamada (≈147 llamadas/día caben en el free tier); un briefing complejo con varios espacios/servicios/ponentes cuesta ≈$0.001/llamada (≈66 llamadas/día en el free tier). En ambos casos, el límite que se agota primero en el free tier es el de tokens/día, no el de peticiones/día. Detalle completo, metodología y limitaciones de la estimación en el propio código del agente (`ESTIMACION_TOKENS.md`, en esta misma carpeta `docs/`).

### 11.2 Checklist de monitoreo continuo
- [ ] **Nota de advertencia:** no hay monitoreo continuo implementado. El agente está en fase beta y toda la garantía de calidad recae en la revisión humana obligatoria.

---

## 12. Casos de prueba (ejemplos de fallo conocidos)

```text
Caso 1: Documento con "Email ponente:" y varios ponentes a la vez.
Resultado obtenido: ese email podía copiarse también en el email del
        cliente, por ser el único email del documento.
Resultado esperado: el email del cliente debe quedar vacío si no hay
        una etiqueta propia de cliente.
Estado: Resuelto — se aisló el heurístico por entidad.

Caso 2: Un mismo texto menciona el estado del PRESUPUESTO y no dice
        nada del estado del EVENTO, pero ambos usan vocabulario similar
        ("pendiente de aprobación").
Resultado obtenido (con un heurístico ingenuo): el estado del evento se
        habría rellenado igualmente, por error, a partir de la frase
        sobre el presupuesto.
Resultado esperado: el estado del evento solo debe rellenarse si el
        documento lo etiqueta explícitamente como tal.
Estado: Resuelto por diseño — el estado del evento nunca se detecta por
        heurístico de texto libre, solo por etiqueta explícita.

Caso 3: Varios espacios candidatos mencionados a la vez para comparar.
Resultado obtenido: solo se propone un espacio como estructurado; el
        resto queda resumido como texto libre.
Resultado esperado: sería deseable poder proponer varios espacios como
        una lista.
Estado: Conocido, sin resolver — requiere ampliar el esquema de datos.

Caso 4: Briefing con varios ponentes en bloques numerados ("Ponente 1",
        "Ponente 2"...), cada uno con sus propias líneas "Nombre:",
        "Empresa:", "Email:" (sin cualificar, no "Email ponente:").
Resultado obtenido (antes de corregirlo): 0 ponentes detectados
        (detectar_ponentes() solo reconocía una lista en una línea);
        además, nombre_evento y cliente.cliente/email/telefono se
        contaminaban con los datos del ÚLTIMO ponente del documento,
        porque "nombre"/"empresa" eran sinónimos ambiguos y el chequeo
        de "email ya reclamado por un ponente" solo miraba etiquetas
        cualificadas, no genéricas dentro de un bloque.
Resultado esperado: los 4 ponentes detectados con sus campos propios;
        nombre_evento y cliente sin contaminar.
Estado: Resuelto — ver versión 1.2.0 en el historial (sección 13).
```

---

## 13. Historial de versiones del agente

| Versión | Fecha | Cambios principales | Modelo LLM usado |
|---|---|---|---|
| 1.0.0 | 09/07/2026 | Primera ficha de la implementación real, en paralelo a la arquitectura objetivo de `Agente_OPERIS.md`. Motor de reglas (gratis, determinista) + motor LLM (Groq `openai/gpt-oss-120b`) intercambiables, estructurados según el precedente real de `Agente_04_Copilot_Raul/lumen_agente_04/`. | `openai/gpt-oss-120b` |
| 1.1.0 | 09/07/2026 | A petición del cliente, `evento.fecha_inicio`/`fecha_fin` y `presupuesto.fecha` pasan a devolverse en `DD/MM/AAAA` en vez de en ISO (`AAAA-MM-DD`). Los dos motores siguen trabajando internamente en ISO; la conversión se hace en un único punto compartido (`src/schemas.py::generar_aviso_y_validacion`). Como consecuencia, esos tres campos ya no coinciden con el formato real de `eventos.csv`/`presupuestos.csv` — el backend/orquestador deberá reconvertirlos antes de un `INSERT`. | `openai/gpt-oss-120b` |
| 1.2.0 | 09/07/2026 | Corregidos varios bugs de contaminación cruzada y una limitación real detectados al probar `briefing_complejo.txt` con el motor de reglas: (1) `"nombre"`/`"empresa"` eran sinónimos ambiguos de `nombre_evento`/`cliente` en `field_aliases_3.py` — con varios ponentes etiquetados (`Nombre:`, `Empresa:` por cada uno), el ÚLTIMO ponente del documento contaminaba esos dos campos; se quitaron esos sinónimos. (2) El mismo patrón afectaba a `cliente.email`/`cliente.telefono` cuando el documento no usa etiquetas cualificadas (`Email ponente:`) sino genéricas (`Email:`) dentro de cada bloque de ponente; se corrigió comparando el valor candidato contra los emails/teléfonos ya detectados de los ponentes. (3) `detectar_ponentes()` no reconocía bloques numerados (`Ponente 1` / `Ponente 2`...), solo listas en una línea — ahora sí, con extracción por bloque de nombre, DNI, email, teléfono, empresa, cargo, sector y hotel (los campos en prosa libre, como horario o tipo de ponencia, se dejan vacíos a propósito). (4) `detectar_nombre_evento()` no toleraba una palabra intermedia ("organización **integral** del...") ni un nombre de evento partido en dos líneas físicas del documento original — ambos casos, ya cubiertos. Con estos cuatro arreglos, `briefing_complejo.txt` pasa de detectar 0 ponentes y contaminar `nombre_evento`/`cliente` a detectar los 4 ponentes correctamente y el nombre real del evento. | `openai/gpt-oss-120b` |

**Próximos pasos previstos:**
1. Primera prueba real del motor LLM con clave de Groq (hasta ahora solo probado el motor de reglas).
2. Conectar una interfaz de revisión humana (Streamlit u otra) a esta implementación — los prototipos actuales usan una versión anterior del motor.
3. Si el caso de uso lo justifica, ampliar el esquema para modelar varios espacios candidatos como lista (como ya ocurre con los ponentes).
4. Integrar con el orquestador del proyecto cuando exista (hoy `agente_operis` ya expone el contrato `ejecutar_agente(payload)` que ese orquestador necesitaría).

---

## 14. Referencias y recursos adicionales

- Documentación técnica completa (código, contratos, casos de prueba): [`README.md`](../README.md), en la raíz de esta misma carpeta del agente.
- Arquitectura objetivo / aspiracional: `Agente_OPERIS.md`
- Precedente real de estructura seguido: `Agente_04_Copilot_Raul/lumen_agente_04/`
- Plantilla de agente dependiente de referencia: `Definicion_Agentes_RAUL/README_plantilla_agente_dependiente.md`
- Contrato de API del proyecto: `API_Nora/api/contrato_api_eventos_2.md`
- CSV de referencia de la base de datos: `Datos_alimentación_bbdd_Leire_Eduardo/`
- Canal de soporte / contacto: Ainara / David

**Nota sobre la bandeja de correo (descartado por ahora):** se valoró que el agente leyera directamente una bandeja de entrada en vez de recibir el texto ya extraído de un documento. Es técnicamente viable (IMAP con librería estándar de Python, o la API del proveedor de correo con OAuth2), pero implica infraestructura nueva (buzón dedicado, disparo periódico, deduplicación de correos ya procesados) y cambia el disparo del agente de manual a automático. Se decidió no incluirlo en esta iteración; queda como posible fase 2.

---

## Apéndice: Checklist final antes de publicar la documentación

- [x] ¿Puede entenderla alguien que no conoce el diseño interno? — Sí; usa la misma analogía del "becario rápido" que `Agente_OPERIS.md`.
- [x] ¿Está documentado el razonamiento, no solo la API? — Sí; sección 4.
- [x] ¿Hay al menos un ejemplo real de entrada + salida? — Sí; sección 3.3.
- [x] ¿Están los modos de fallo con síntoma, causa y recuperación? — Sí; sección 5.
- [x] ¿Se puede reproducir una sesión fallida? — El motor de reglas sí, exactamente (determinista); el motor LLM de forma aproximada (`temperature=0`).
- [x] ¿Están marcados los componentes no deterministas y sus salvaguardas? — Sí; sección 7.
- [x] ¿Son honestos y explícitos los límites del agente? — Sí; sección 2, incluyendo limitaciones de esquema conocidas y sin resolver.
