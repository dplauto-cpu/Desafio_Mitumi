# Estructura de `agente_telegram_ponentes`

```text
src/agents/agente_telegram_ponentes/
├── README.md
├── GUIA_SIMPLE_PRUEBA.md
├── ESTRUCTURA.md
├── main.py
├── servicio.py
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── config/
│   ├── settings.py
│   ├── permisos.py
│   └── fuentes.py
├── prompts/
│   ├── prompt_sistema.md
│   ├── prompt_analisis.md
│   ├── prompt_borrador.md
│   ├── prompt_validacion.md
│   └── README.md
├── src/
│   ├── agente.py
│   ├── schemas.py
│   ├── funciones.py
│   ├── herramientas.py
│   ├── rag.py
│   ├── memoria.py
│   └── validaciones.py
├── inputs/
│   ├── payload_demo.json
│   └── ejemplos/
├── integrations/
│   ├── api_backend.py
│   ├── telegram.py
│   ├── llm.py
│   └── documentos.py
├── data/
│   ├── mock/
│   ├── rag/
│   ├── pdf/
│   ├── procedimientos/
│   └── ejemplos/
├── outputs/
│   ├── borradores/
│   ├── informes/
│   └── respuestas_json/
└── logs/
```

Interfaz no modificable:

```python
def ejecutar_agente(payload: dict) -> dict:
    ...
```
