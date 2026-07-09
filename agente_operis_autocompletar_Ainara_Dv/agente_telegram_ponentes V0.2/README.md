# README — agente_telegram_ponentes

Proyecto: **Gestión Inteligente de Eventos**  
Componente: **Agente especializado de atención a ponentes por Telegram**  
Estado: **MVP local / preparado para integración futura con orquestador y backend**

---

## 0. Principio arquitectónico

Este agente puede ejecutarse de forma local para pruebas:

```bash
python main.py
```

Pero en la arquitectura final **no será un agente autónomo**. Será llamado por el **agente orquestador** mediante la función obligatoria:

```python
def ejecutar_agente(payload: dict) -> dict:
    ...
```

Flujo final previsto:

```text
Backend / Orquestador
        ↓
ejecutar_agente(payload)
        ↓
agente_telegram_ponentes
        ↓
respuesta estructurada
        ↓
Orquestador / Backend / Validación humana
```

Regla principal:

```text
El agente analiza, interpreta, redacta y propone.
El orquestador coordina y enruta.
El backend valida, guarda y ejecuta acciones reales.
El humano aprueba acciones sensibles.
La BBDD es la fuente final de verdad.
```

---

## 1. Regla crítica no modificable

La estructura interna puede adaptarse, pero **la comunicación con el orquestador no se modifica**.

Archivo obligatorio:

```text
src/agente.py
```

Función obligatoria:

```python
def ejecutar_agente(payload: dict) -> dict:
    ...
```

También es obligatorio:

```text
1. Mismo contrato de entrada.
2. Mismo contrato de salida.
3. Salida siempre estructurada.
4. Ningún agente invoca directamente a otro agente.
5. Ningún agente escribe directamente en la BBDD final.
6. Ningún agente ejecuta acciones externas reales sin permiso y sin validación cuando aplique.
```

---

## 2. Qué hace este agente

Este agente atiende consultas de ponentes por Telegram usando datos del backend o, en pruebas locales, datos mock.

Capacidades MVP:

- identifica al ponente por `telegram_user_id`;
- localiza sus eventos activos;
- responde dudas sobre hotel, viaje, horario, lugar y documentación pendiente;
- genera borradores de respuesta Telegram;
- detecta bloqueos: ponente no identificado, varios eventos activos, datos incompletos;
- escala a organización cuando falta información o hay baja confianza;
- registra trazabilidad local en `logs/`;
- devuelve siempre salida estructurada al orquestador/backend.

---

## 3. Qué NO hace

El agente no debe:

- confirmar vuelos, hoteles, taxis ni cambios logísticos;
- aprobar documentación del ponente;
- modificar datos del evento;
- escribir directamente en la BBDD final;
- enviar mensajes reales si `ALLOW_SEND_TELEGRAM=False`;
- enviar mensajes que requieren validación humana;
- invocar directamente a otros agentes;
- sustituir al orquestador o al backend.

---

## 4. Estructura conceptual

```text
src/agents/agente_telegram_ponentes/
│
├── README.md
│   └── Documenta objetivo, límites, ejecución local e integración futura.
│
├── main.py
│   └── Ejecuta una prueba local leyendo inputs/payload_demo.json.
│
├── servicio.py
│   └── Servicio local opcional para recibir y responder Telegram por polling.
│
├── .env
│   └── Configuración real local: LLM, API keys, Telegram, permisos, backend y rutas.
│
├── .env.example
│   └── Plantilla sin secretos para que cualquier equipo configure su entorno.
│
├── config/
│   ├── settings.py
│   ├── permisos.py
│   └── fuentes.py
│   └── Lee .env y centraliza configuración, permisos y rutas.
│
├── prompts/
│   ├── prompt_sistema.md
│   ├── prompt_analisis.md
│   ├── prompt_borrador.md
│   ├── prompt_validacion.md
│   └── README.md
│   └── Instrucciones específicas que se pasan al LLM.
│
├── src/
│   ├── agente.py
│   ├── schemas.py
│   ├── funciones.py
│   ├── herramientas.py
│   ├── rag.py
│   ├── memoria.py
│   └── validaciones.py
│   └── Código interno del agente. Aquí está la interfaz crítica ejecutar_agente(payload).
│
├── inputs/
│   └── Payloads o entradas de demo.
│
├── integrations/
│   ├── api_backend.py
│   ├── telegram.py
│   ├── llm.py
│   └── documentos.py
│   └── Conectores específicos: backend/mock, Telegram, LLM y documentos.
│
├── data/
│   ├── mock/
│   ├── rag/
│   ├── pdf/
│   ├── procedimientos/
│   └── ejemplos/
│   └── Datos propios del agente para pruebas, RAG o documentación local.
│
├── outputs/
│   ├── borradores/
│   ├── informes/
│   └── respuestas_json/
│   └── Salidas generadas por el agente.
│
└── logs/
    └── Trazabilidad de ejecuciones, decisiones, errores y resultados.
```

---

## 5. Contrato común de entrada

Todos los agentes deben aceptar este formato mínimo:

```json
{
  "id_evento": 10,
  "id_registro": null,
  "tipo_peticion": "responder_consulta_ponente_telegram",
  "origen": "orquestador",
  "usuario_solicitante": "111111",
  "rol_usuario": "ponente",
  "datos": {
    "telegram_user_id": "111111",
    "telegram_chat_id": "111111",
    "texto": "¿En qué hotel me alojo?"
  },
  "contexto": {
    "fase_evento": "ponentes",
    "canal": "telegram"
  },
  "modo": "propuesta"
}
```

Campos críticos:

| Campo | Uso |
|---|---|
| `id_evento` | Evento sobre el que trabaja el agente. Puede ser `null` si se debe deducir. |
| `id_registro` | Registro concreto si aplica. |
| `tipo_peticion` | Qué se pide al agente. |
| `origen` | `orquestador`, `backend`, `frontend`, `telegram`, `manual`, `demo`. |
| `usuario_solicitante` | Usuario o sistema que activa la petición. |
| `rol_usuario` | `ponente`, `organizador`, `admin`, `sistema`. |
| `datos` | Datos específicos de Telegram y consulta. |
| `contexto` | Información general del evento/canal. |
| `modo` | `simulacion`, `propuesta`, `ejecucion_controlada`. |

---

## 6. Contrato común de salida

El agente devuelve siempre:

```json
{
  "ok": true,
  "agente": "agente_telegram_ponentes",
  "tipo_peticion": "responder_consulta_ponente_telegram",
  "resumen": "Consulta de ponente clasificada como consulta_alojamiento.",
  "datos_detectados": {},
  "acciones_propuestas": [],
  "bloqueos_detectados": [],
  "borradores_generados": [],
  "requiere_validacion_humana": false,
  "nivel_riesgo": "bajo",
  "errores": [],
  "trazas": {}
}
```

Los mensajes para Telegram se devuelven como borradores:

```json
{
  "canal": "telegram",
  "destinatario": "111111",
  "texto": "Tu alojamiento es: Hotel NH Aránzazu...",
  "apto_envio_automatico": true,
  "requiere_revision": false
}
```

---

## 7. Flujo interno

```text
1. Recibe payload común.
2. Valida contrato de entrada.
3. Extrae datos Telegram.
4. Identifica ponente por telegram_user_id.
5. Consulta eventos activos del ponente.
6. Si hay varios eventos, pide aclaración.
7. Consulta datos del ponente en el evento.
8. Consulta RAG si está activado.
9. Llama al LLM o usa fallback determinista.
10. Construye respuesta con datos confirmados.
11. Devuelve salida estructurada.
12. Registra trazabilidad local.
```

---

## 8. `.env`

Cada equipo configura su propio `.env`.

Variables principales:

```env
LLM_PROVIDER=groq
LLM_API_KEY=
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant

TELEGRAM_ENABLED=False
TELEGRAM_BOT_TOKEN=
ALLOW_SEND_TELEGRAM=False

BACKEND_ENABLED=False
BACKEND_BASE_URL=http://localhost:8000

ALLOW_BACKEND_WRITE=False
ALLOW_DB_WRITE=False
ALLOW_EXTERNAL_SEND=False
ALLOW_AUTO_APPROVAL=False
```

Reglas:

```text
.env contiene valores reales y secretos locales.
.env.example contiene plantilla sin secretos.
.env no debe subirse al repositorio.
```

---

## 9. Ejecución local

```bash
cd src/agents/agente_telegram_ponentes
python -m venv .venv
.venv\Scriptsctivate
pip install -r requirements.txt
python main.py
```

La ejecución local:

```text
1. Lee inputs/payload_demo.json.
2. Llama a ejecutar_agente(payload).
3. Muestra resultado en consola.
4. Guarda salida en outputs/respuestas_json/ultima_respuesta.json.
```

---

## 10. Ejecución Telegram local opcional

Solo cuando el equipo quiera probar Telegram real:

```env
TELEGRAM_ENABLED=True
TELEGRAM_BOT_TOKEN=token_real
ALLOW_SEND_TELEGRAM=True
```

Después:

```bash
python servicio.py
```

El servicio solo envía respuesta automática si:

```text
ALLOW_SEND_TELEGRAM=True
requiere_validacion_humana=False
existe borrador Telegram generado
```

---

## 11. Modo seguro por defecto

```text
BACKEND_ENABLED=False
ALLOW_BACKEND_WRITE=False
ALLOW_DB_WRITE=False
ALLOW_EXTERNAL_SEND=False
ALLOW_AUTO_APPROVAL=False
ALLOW_SEND_TELEGRAM=False
```

Esto permite probar el agente sin tocar sistemas reales.

---

## 12. Integración futura con orquestador

El orquestador no debe conocer la lógica interna del agente. Solo debe construir el payload y llamar:

```python
from src.agente import ejecutar_agente

respuesta = ejecutar_agente(payload)
```

El agente devuelve el contrato común y el orquestador/backend decidirá qué mostrar, guardar o ejecutar.
