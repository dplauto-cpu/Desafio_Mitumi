# Guía simple para probar `agente_telegram_ponentes`

Esta guía solo enumera los ítems que habrá que configurar o decidir. Cada punto se desarrollará después cuando el usuario lo pida.

## 1. Preparar carpeta del agente

- Colocar el agente en `src/agents/agente_telegram_ponentes/`.
- Abrir terminal en esa carpeta.
- Crear entorno virtual.
- Instalar `requirements.txt`.

## 2. Revisar `.env`

- Confirmar `AGENT_NAME=agente_telegram_ponentes`.
- Confirmar `MODO_DEMO=True` para pruebas locales.
- Confirmar `ORQUESTADOR_ENABLED=False` mientras no se use el orquestador.
- Confirmar permisos seguros: `ALLOW_BACKEND_WRITE=False`, `ALLOW_DB_WRITE=False`, `ALLOW_EXTERNAL_SEND=False`.

## 3. Elegir modelo LLM

- Elegir proveedor: Groq, OpenAI, Anthropic u otro compatible.
- Elegir modelo.
- Obtener API key.
- Configurar `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`.
- Decidir temperatura y límite de tokens.

## 4. Elegir modo de prueba

- Prueba sin LLM: dejar `LLM_API_KEY` vacío y usar fallback por reglas.
- Prueba con LLM: configurar API key y modelo.
- Prueba sin Telegram real: ejecutar `python main.py`.
- Prueba con Telegram real: ejecutar `python servicio.py`.

## 5. Configurar Telegram si se prueba real

- Crear bot en Telegram.
- Obtener `TELEGRAM_BOT_TOKEN`.
- Decidir teléfono/cuenta desde la que se escribirá al bot.
- Obtener o comprobar `telegram_user_id`.
- Añadir ese `telegram_user_id` a `data/mock/ponentes.json`.
- Activar `TELEGRAM_ENABLED=True`.
- Activar `ALLOW_SEND_TELEGRAM=True` solo cuando se quiera responder realmente.

## 6. Revisar datos mock

- Revisar `data/mock/ponentes.json`.
- Revisar `data/mock/eventos_ponente.json`.
- Revisar `data/mock/ponente_evento.json`.
- Confirmar que el `telegram_user_id` del payload existe en los mocks.
- Confirmar que el ponente tiene evento activo.

## 7. Revisar payload de entrada

- Abrir `inputs/payload_demo.json`.
- Confirmar `id_evento`.
- Confirmar `tipo_peticion`.
- Confirmar `datos.telegram_user_id`.
- Confirmar `datos.texto`.

## 8. Ejecutar prueba local

- Ejecutar `python main.py`.
- Revisar salida en consola.
- Revisar `outputs/respuestas_json/ultima_respuesta.json`.
- Revisar `logs/conversaciones.jsonl`.

## 9. Validar contrato con orquestador

- Confirmar que la entrada respeta el contrato común.
- Confirmar que la salida contiene: `ok`, `agente`, `resumen`, `datos_detectados`, `acciones_propuestas`, `bloqueos_detectados`, `borradores_generados`, `requiere_validacion_humana`, `nivel_riesgo`, `errores`, `trazas`.

## 10. Preparar conexión futura al backend

- Esperar endpoints del equipo Fullstack.
- Configurar `BACKEND_ENABLED=True`.
- Configurar `BACKEND_BASE_URL`.
- Configurar `BACKEND_API_KEY` si aplica.
- Adaptar `integrations/api_backend.py` si los endpoints finales cambian.
