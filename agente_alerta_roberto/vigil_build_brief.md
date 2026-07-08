# Vigil — Build Brief (MVP)

> Especificación para construir el agente. El razonamiento y las alternativas descartadas viven en `vigil_plan_inicial.md` — este documento es autosuficiente para empezar a construir, no hace falta leer el otro.

## Instrucciones para quien construya esto

- Implementa solo lo descrito aquí. No añadas funcionalidades, ficheros, frameworks o dependencias que no estén mencionados en este documento.
- No inventes datos: cuando un campo no se pueda extraer de un pliego, o no se pueda verificar contra el perfil de Mitumi, márcalo explícitamente como tal — nunca lo rellenes por intuición.
- Es un MVP para una demo: prioriza que el flujo funcione de principio a fin sobre que cada pieza sea perfecta.

---

## 1. Qué construir (una frase)

Un script en Python que, cada mañana, consulta la Plataforma de Contratación Pública de Euskadi filtrando por las tres diputaciones forales (Araba, Gipuzkoa, Bizkaia), extrae y filtra las licitaciones relevantes para Mitumi (agencia de eventos), y envía un email con el resumen a una lista de destinatarios configurada.

## 2. Stack técnico

| Pieza | Elección |
|---|---|
| Lenguaje | Python 3.x |
| LLM | Groq API — **ver aviso justo abajo, es importante** |
| Lectura de la fuente | `requests` + `BeautifulSoup4`. Si la plataforma renderiza con JS y no funciona, usar Playwright como fallback — validar esto es lo primero que hay que hacer al empezar a construir |
| Structured output | Pydantic v2 |
| Persistencia (dedupe) | SQLite local (un fichero `.db` en el propio proyecto) |
| Envío de email | `smtplib` con una cuenta y contraseña de aplicación, o una API tipo Resend — lo que resulte más simple de configurar |
| Programación | GitHub Actions, workflow con `schedule: cron` — entorno separado de la plataforma de Mitumi (Ágora) |
| Explícitamente fuera | Nada de FastAPI, Django, Celery, Airflow, ni un servidor propio. Es un batch diario, no un servicio siempre encendido. |

> ⚠️ **Aviso sobre el modelo (comprobado el 8 de julio de 2026):** Groq anunció el 17 de junio de 2026 la retirada de `llama-3.3-70b-versatile` y `llama-3.1-8b-instant`, con **fecha de apagado el 16 de agosto de 2026**. Hoy el modelo sigue funcionando con normalidad, así que sirve para una demo a corto plazo. Pero si Vigil va a seguir usándose después de esa fecha, hay que migrar a `openai/gpt-oss-120b` (reemplazo recomendado por el propio Groq, mismo proveedor, mismo SDK). **Decisión sugerida:** si la demo es antes de mediados de agosto de 2026, usar `llama-3.3-70b-versatile` tal como se pidió; si no, empezar directamente con `openai/gpt-oss-120b` para no tener que migrar después. Quien construya esto debería confirmar la fecha de la demo antes de fijar el modelo.

## 3. Alcance del MVP (implementar esto, y solo esto)

- [ ] Consultar la Plataforma de Contratación Pública de Euskadi (KontratazioA — `contratacion.euskadi.eus`) filtrando por las tres diputaciones forales: Araba, Gipuzkoa y Bizkaia.
- [ ] Extraer y estructurar cada convocatoria nueva: objeto del contrato, órgano convocante, importe, plazo de presentación, enlace al pliego.
- [ ] Filtrar por relevancia combinando (a) un filtro semántico con el LLM y (b) el perfil de Mitumi de la sección 6 — no coincidencia de palabras clave sueltas.
- [ ] Evitar duplicados entre ejecuciones (SQLite: guardar el ID/URL de cada convocatoria ya procesada).
- [ ] Enviar un email diario con el resumen de las alertas relevantes del día, a la lista de destinatarios de la configuración (dirección ficticia para la demo).

## 4. Fuera de alcance (no implementar en el MVP)

- Historial de licitaciones con retroalimentación (ganado/perdido) — dejar el módulo como estructura vacía, sin lógica.
- Consultar fuentes fuera de las tres diputaciones forales (nada de PLACSP estatal ni TED europeo).
- Preparar documentación de oferta o redactar propuestas.
- Seguimiento del proceso una vez presentada una oferta.
- Análisis legal o de solvencia de los pliegos.
- Cualquier interfaz web, dashboard o panel — el único output es el email.
- Reintentos automáticos sofisticados — un log del error basta para el MVP (ver sección 9).

## 5. Fuente de datos

- Portal: Plataforma de Contratación Pública de Euskadi / KontratazioA — `https://www.contratacion.euskadi.eus/webkpe00-kpeperfi/es/ac70cPublicidadWar/busquedaAnuncios?locale=es`
- Filtrar por poder adjudicador: las tres diputaciones forales (Araba, Gipuzkoa, Bizkaia). Centraliza también cientos de otros poderes adjudicadores vascos — no usar esos, solo las tres diputaciones.
- **Primera tarea técnica al empezar a construir**: comprobar si esta URL se puede leer con `requests` + `BeautifulSoup`, o si la tabla de resultados se renderiza con JavaScript y hace falta Playwright. No está validado todavía.

## 6. Perfil de Mitumi (contexto fijo para el filtro de relevancia — `business_profile.py`)

Usar este bloque tal cual como contexto del LLM en el paso de relevancia. Construido a partir de la web de Mitumi y documentos reales, no es especulativo.

```text
QUIÉN ES: Agencia de eventos boutique con sede en Vitoria-Gasteiz. Equipo
reducido de forma deliberada, apoyado en una red de colaboradores externos
(comunicación, diseño digital, fotografía, sonido).

TIPOS DE EVENTO QUE ORGANIZA:
- Eventos corporativos (family days, encuentros internos, inauguraciones,
  aniversarios)
- Entregas de premios (con secretaría técnica y protocolo)
- Marketing experiencial y eventos de calle (ferias, activaciones de marca,
  presentaciones de producto)
- Congresos y asambleas, tanto empresariales como INSTITUCIONALES (gestión
  del espacio, ponentes, catering; presencial, virtual o híbrido)
- Eventos gastronómicos — especialidad de la casa (showcookings, catas,
  degustaciones, talleres)
- Formación en creatividad, procesos participativos y de escucha, diseño
  gráfico

FUERA DE PERFIL: fiestas privadas (bodas, comuniones, bautizos) — no
relevante para contratación pública.

TRACK RECORD CON EL SECTOR PÚBLICO:
- Cliente institucional recurrente: Ayuntamiento de Vitoria-Gasteiz
  (campañas de comercio urbano, congresos, festivales, campañas de
  sensibilización).
- Cliente recurrente: Diputación Foral de Álava, varios proyectos.
- Trabaja también con entes semipúblicos de Álava: BIC Araba, Egibide,
  Cámara de Comercio de Álava, Tuvisa, CIC energiGUNE.
- SIN historial conocido de contratos en Bizkaia o Gipuzkoa — tratar esos
  territorios como oportunidad de expansión, no como trayectoria
  consolidada.
- Los proyectos institucionales conocidos parecen sobre todo contratos
  directos o de importe menor, no grandes licitaciones formales — no
  asumir trayectoria en concursos de gran volumen.

ESCALA: agencia boutique — formato pequeño-mediano (decenas a varios
cientos de asistentes), no macroproducciones. Tiene acceso a recintos
mucho más grandes (hasta miles de asistentes) a través de su red, pero
no es su terreno habitual.

ZONA GEOGRÁFICA: núcleo en Vitoria-Gasteiz/Araba, opera con normalidad
en toda la Comunidad Autónoma del País Vasco. Logística de ponentes con
alcance nacional.

NO VERIFICABLE — no asumir ni en un sentido ni en otro, marcar como tal
si el pliego lo exige:
- Certificaciones formales (ISO 20121 u otras de gestión sostenible de
  eventos)
- Facturación / clasificación empresarial
```

## 7. Estructura de módulos

```text
vigil/
├── main.py               → entry point, orquesta el flujo de la sección 8
├── config.py              → fuentes activas, umbrales, destinatarios, credenciales (via variables de entorno)
├── sources.py             → lectura de KontratazioA filtrada por las 3 diputaciones
├── extractor.py           → LLM + Pydantic: convocatoria → JSON estructurado
├── business_profile.py    → el bloque de texto de la sección 6, expuesto como constante/función
├── relevance.py           → filtro semántico: LLM + business_profile.py → veredicto + motivo
├── history.py              → módulo vacío/stub, sin lógica — preparado para fase 2, no lo implementes ahora
├── dedupe.py              → SQLite: registra qué convocatorias ya se procesaron
├── notifier.py            → construye y envía el email (smtplib o API)
├── schemas.py             → modelos Pydantic: Convocatoria, VeredictoRelevancia, etc.
├── tests/
└── examples/               → un par de convocatorias de ejemplo (reales o simuladas) para probar el pipeline sin depender de que haya novedades ese día
```

## 8. Flujo de ejecución (end-to-end)

```text
1. Disparo programado (GitHub Actions, hora configurable — propuesta 07:00 Europe/Madrid)
2. sources.py    → consulta KontratazioA, filtra por las 3 diputaciones
3. dedupe.py     → descarta lo ya procesado en ejecuciones anteriores
4. extractor.py  → por cada convocatoria nueva: LLM + Pydantic → objeto estructurado
5. relevance.py  → LLM + business_profile.py → relevante / no relevante + motivo
6. dedupe.py     → registra como procesado (independientemente del resultado del filtro)
7. notifier.py   → si hay al menos una convocatoria relevante, construye y envía el email
8. Logging       → registrar qué se procesó, qué se filtró y por qué (ver sección 9)
```

## 9. Configuración y manejo de errores (mínimo viable)

**Variables de entorno necesarias:**
- `GROQ_API_KEY`
- Credenciales de envío de email (SMTP o API key)
- `DESTINATARIOS` (lista de direcciones — ficticia para la demo)
- `CRON_HORA` (propuesta: `07:00`, zona horaria `Europe/Madrid`)
- Ruta del fichero SQLite

**Errores — comportamiento mínimo para el MVP:**
- Si falla la lectura de la fuente → loguear el error y terminar la ejecución sin enviar email (no hay nada que reportar).
- Si el LLM falla al procesar una convocatoria concreta → loguear, marcarla como "no procesada" (no la marques como vista en `dedupe.py`, para que se reintente al día siguiente), continuar con las demás.
- Si falla el envío del email → loguear el error. No hace falta reintento automático en el MVP.

## 10. Formato del email de salida

- **Asunto**: algo tipo `Vigil — N concursos relevantes hoy (Araba/Gipuzkoa/Bizkaia)`
- **Por cada concurso relevante, incluir**: título/objeto, órgano convocante, importe, plazo de presentación, enlace al pliego, y el motivo del encaje que dio `relevance.py` (no solo "es relevante", sino por qué — igual que en el ejemplo del Anexo A del plan).
- Si algún campo no se pudo verificar contra el perfil de Mitumi (sección 6), indicarlo explícitamente en el email en vez de omitirlo u omitir la duda.

## 11. Criterios de aceptación (para saber que el MVP "funciona")

- [ ] Ejecutado manualmente (sin esperar al cron), el script recorre las tres diputaciones sin fallar.
- [ ] Las convocatorias encontradas se estructuran correctamente en el schema de Pydantic.
- [ ] El filtro de relevancia distingue casos reales: una convocatoria claramente de eventos/congresos se marca relevante con un motivo coherente; una convocatoria de otro sector (obra pública, suministros médicos, etc.) se descarta.
- [ ] Ejecutar el script dos veces seguidas con las mismas convocatorias no genera un segundo email duplicado.
- [ ] El email llega a la dirección configurada con el formato de la sección 10.
- [ ] El workflow de GitHub Actions se dispara solo a la hora configurada, sin intervención manual.
