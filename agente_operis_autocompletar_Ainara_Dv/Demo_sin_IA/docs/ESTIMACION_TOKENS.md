# Estimación de uso de tokens — motor LLM de Operis

Generado automáticamente por `docs/estimacion_tokens.py`. Modelo: `openai/gpt-oss-120b` en Groq. Codificación usada para estimar tokens: `o200k_base` (aproximación — ver metodología en la cabecera de `estimacion_tokens.py`).

Precios: $0.15/1M tokens entrada, $0.6/1M tokens salida. Free tier: 1000 peticiones/día, 200,000 tokens/día.

## Resumen comparativo

| | Simple (briefing_prueba.txt) | Complejo (briefing_complejo.txt) |
|---|---|---|
| Caracteres del briefing | 1,052 | 3,642 |
| Tokens del prompt de sistema (fijo) | 799 | 799 |
| Tokens del texto del briefing | 226 | 935 |
| Tokens de entrada totales | 1,025 | 1,734 |
| Tokens de salida (JSON estimado) | 335 | 1,273 |
| Tokens totales por llamada | 1,360 | 3,007 |
| Coste entrada (USD) | $0.000154 | $0.000260 |
| Coste salida (USD) | $0.000201 | $0.000764 |
| Coste total por llamada (USD) | $0.000355 | $0.001024 |
| Llamadas/día posibles en free tier | 147 | 66 |
| Límite que se agota primero | tokens/día | tokens/día |

## Lectura de los resultados

- El **prompt de sistema pesa lo mismo en los dos casos** (es fijo, define el esquema) y es la parte dominante del coste de entrada en el caso simple — normal en una tarea de extracción de un solo documento corto: el "overhead" fijo del esquema pesa más que el propio texto.
- En el caso complejo, el texto de entrada y sobre todo la salida (4 ponentes con toda su ficha de logística) crecen mucho más que proporcionalmente al número de líneas del briefing — la lista de ponentes es la parte más cara de la respuesta.
- **Limitación de esquema detectada al construir el caso complejo:** el bloque `espacio` es un único objeto, no una lista — no modela bien un briefing que compara varios espacios candidatos a la vez (aquí, BEC / Palacio Euskalduna / Artium Museoa). En la estimación, el espacio principal se guarda en `espacio` y las alternativas quedan resumidas como texto en `espacio.nota`. Si este caso de uso (comparar espacios) es habitual, `espacio` debería pasar a ser una lista, igual que `ponentes` — no se ha tocado el esquema ahora para no romper la compatibilidad con las apps ya hechas, pero queda anotado para una futura iteración.
- En los dos casos, el límite que se agota primero en el free tier es el de **tokens/día** (200.000), no el de peticiones/día (1000): con briefings de este tamaño se llega a 66–147 llamadas/día antes de agotar tokens, muy por debajo del límite de peticiones. Es decir, para este agente el free tier de Groq rinde menos peticiones de las 1000 nominales — al contrario que en Vigil, cuyas convocatorias de licitación son más cortas y sí llegarían a agotar antes las peticiones/día que los tokens/día.
