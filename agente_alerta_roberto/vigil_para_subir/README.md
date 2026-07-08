# Vigil — agente de alertas de licitaciones para Mitumi

Vigil es un agente que, cada mañana, consulta la Plataforma de Contratación
Pública de Euskadi (KontratazioA) para las tres diputaciones forales
(Araba, Gipuzkoa y Bizkaia), filtra las licitaciones relevantes para Mitumi
(agencia de eventos) usando un modelo de lenguaje, y envía un email con el
resumen del día.

## Cómo funciona (flujo)

1. **sources.py** → lee la web de KontratazioA con Playwright y saca las convocatorias de las 3 diputaciones.
2. **dedupe.py** → descarta las que ya se procesaron en días anteriores (SQLite).
3. **extractor.py** → convierte cada convocatoria en datos limpios (Groq + Pydantic).
4. **relevance.py** → decide si encaja con el perfil de Mitumi y explica por qué.
5. **notifier.py** → si hay algo relevante, construye y envía el email.
6. **main.py** → orquesta todo el proceso de principio a fin.

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

Necesita estas variables de entorno (credenciales):

- `GROQ_API_KEY` — clave de la API de Groq
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` — datos del correo saliente
- `DESTINATARIOS` — direcciones que reciben el email, separadas por comas

Con eso puesto:

```bash
python -m vigil.main
```

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
